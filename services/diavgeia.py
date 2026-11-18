"""Read-only client for Diavgeia's OpenData JSON API."""

from collections import OrderedDict
from copy import deepcopy
import logging
import re
from threading import Lock
from time import monotonic
from urllib.parse import quote

import requests

from config import (
    DECISIONS_CACHE_SECONDS, DIAVGEIA_API_URL, DIAVGEIA_TIMEOUT,
    ORGANIZATIONS_CACHE_SECONDS,
)

logger = logging.getLogger(__name__)


class DiavgeiaError(Exception):
    """The upstream service failed or returned an invalid response."""


def document_url(ada):
    return f"https://diavgeia.gov.gr/doc/{quote(ada, safe='')}"


class DiavgeiaClient:
    def __init__(self):
        self._cache = OrderedDict()
        self._lock = Lock()

    def _cached(self, key, ttl, fetch):
        now = monotonic()
        with self._lock:
            entry = self._cache.get(key)
            if entry and now - entry[0] < ttl:
                self._cache.move_to_end(key)
                return deepcopy(entry[1]), False
        try:
            value = fetch()
        except DiavgeiaError:
            # Stale data is usable for one additional TTL, never indefinitely.
            if entry and now - entry[0] < ttl * 2:
                logger.warning("Serving stale Diavgeia cache for %s", key)
                return deepcopy(entry[1]), True
            raise
        with self._lock:
            self._cache[key] = (monotonic(), deepcopy(value))
            self._cache.move_to_end(key)
            while len(self._cache) > 64:
                self._cache.popitem(last=False)
        return value, False

    def _get(self, path, params=None):
        try:
            with requests.get(
                f"{DIAVGEIA_API_URL}/{path}", params=params,
                timeout=DIAVGEIA_TIMEOUT, headers={"Accept": "application/json"},
            ) as response:
                response.raise_for_status()
                data = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Diavgeia request failed for %s: %s", path, type(exc).__name__)
            raise DiavgeiaError("Diavgeia is temporarily unavailable. Please try again.") from exc
        if not isinstance(data, dict):
            raise DiavgeiaError("Diavgeia returned an invalid response.")
        return data

    def organizations(self):
        def fetch():
            rows = self._get("organizations.json", {"status": "active"}).get("organizations")
            if not isinstance(rows, list):
                raise DiavgeiaError("Diavgeia returned an invalid organization list.")
            organizations = []
            for row in rows:
                if not isinstance(row, dict) or not row.get("uid") or not row.get("label"):
                    continue
                organizations.append({
                    "uid": str(row["uid"]), "label": row["label"],
                    "category": row.get("category"),
                    "supervisorId": str(row["supervisorId"]) if row.get("supervisorId") else None,
                })
            if rows and not organizations:
                raise DiavgeiaError("Diavgeia returned an invalid organization list.")
            return organizations
        return self._cached(("organizations",), ORGANIZATIONS_CACHE_SECONDS, fetch)

    def ministries(self):
        organizations, stale = self.organizations()
        return {
            "organizations": sorted(
                [org for org in organizations if org["category"] == "MINISTRY"],
                key=lambda org: org["label"],
            ),
            "stale": stale,
        }

    def filters(self):
        def options(path, key, decision_types=False):
            rows = self._get(path).get(key)
            if not isinstance(rows, list):
                raise DiavgeiaError("Diavgeia returned invalid filter options.")
            return sorted([
                {"uid": str(row["uid"]), "label": row["label"]}
                for row in rows
                if isinstance(row, dict) and row.get("uid") and row.get("label")
                and (not decision_types or row.get("allowedInDecisions") is True)
            ], key=lambda row: row["label"])

        types, types_stale = self._cached(
            ("types",), ORGANIZATIONS_CACHE_SECONDS,
            lambda: options("types.json", "decisionTypes", decision_types=True),
        )
        themes, themes_stale = self._cached(
            ("themes",), ORGANIZATIONS_CACHE_SECONDS,
            lambda: options("dictionaries/THK.json", "items"),
        )
        return {"decisionTypes": types, "thematicCategories": themes,
                "stale": types_stale or themes_stale}

    def decisions(self, org, page=0, size=20, include_supervised=False,
                  decision_type="", thematic_category=""):
        if not isinstance(org, str) or not re.fullmatch(r"[0-9]{1,20}", org):
            raise ValueError("org must be a numeric organization ID.")
        if type(page) is not int or not 0 <= page <= 10000:
            raise ValueError("page must be between 0 and 10000.")
        if type(size) is not int or not 1 <= size <= 100:
            raise ValueError("size must be between 1 and 100.")
        if type(include_supervised) is not bool:
            raise ValueError("include_supervised must be true or false.")
        for name, value in (("type", decision_type), ("tag", thematic_category)):
            if not isinstance(value, str) or (value and not re.fullmatch(r"[\w.-]{1,40}", value)):
                raise ValueError(f"Invalid {name} filter.")
        organizations, catalog_stale = self.organizations()
        labels = {row["uid"]: row["label"] for row in organizations}
        if org not in labels:
            raise ValueError("Unknown active organization.")
        ids = {org}
        if include_supervised:
            children = {}
            for row in organizations:
                children.setdefault(row["supervisorId"], []).append(row["uid"])
            pending = [org]
            while pending:
                for child in children.get(pending.pop(), []):
                    if child not in ids:
                        ids.add(child)
                        pending.append(child)

        def fetch():
            params = {
                "org": ";".join(sorted(ids)), "page": page, "size": size,
                "sort": "recent", "status": "published",
            }
            if decision_type:
                params["type"] = decision_type
            if thematic_category:
                params["tag"] = thematic_category
            data = self._get("search.json", params)
            rows, info = data.get("decisions"), data.get("info")
            if not isinstance(rows, list) or not isinstance(info, dict):
                raise DiavgeiaError("Diavgeia returned invalid search results.")
            total = info.get("total")
            if type(total) is not int or total < 0:
                raise DiavgeiaError("Diavgeia returned an invalid result count.")
            decisions, seen = [], set()
            for row in rows:
                if not isinstance(row, dict):
                    continue
                ada = row.get("ada")
                if not isinstance(ada, str) or not ada.strip() or ada in seen:
                    continue
                organization_id = str(row.get("organizationId", ""))
                if organization_id not in ids:
                    continue
                seen.add(ada)
                decisions.append({
                    "ada": ada, "subject": row.get("subject") or "—",
                    "organizationId": organization_id,
                    "organizationLabel": labels.get(organization_id, organization_id),
                    "issueDate": row.get("issueDate"),
                    "submissionTimestamp": row.get("submissionTimestamp"),
                    "decisionTypeId": row.get("decisionTypeId"),
                    "thematicCategoryIds": row.get("thematicCategoryIds") or [],
                    "documentUrl": document_url(ada),
                })
            if rows and not decisions:
                raise DiavgeiaError("Diavgeia returned unusable search results.")
            return {
                "decisions": decisions, "page": page, "size": size, "total": total,
                "hasMore": bool(rows) and (page + 1) * size < total,
            }
        result, stale = self._cached(
            ("decisions", tuple(sorted(ids)), page, size, decision_type, thematic_category),
            DECISIONS_CACHE_SECONDS, fetch,
        )
        result["stale"] = stale or catalog_stale
        return result


diavgeia = DiavgeiaClient()
