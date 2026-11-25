"""Read-only client for Diavgeia's OpenData JSON API."""

from collections import OrderedDict
from copy import deepcopy
import logging
import json
import re
from threading import Lock
from time import monotonic
from urllib.parse import quote

import requests

from services.search_filters import validate_filters, advanced_query

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

    @staticmethod
    def _organization_rows(rows):
        if not isinstance(rows, list):
            raise DiavgeiaError("Diavgeia returned an invalid organization list.")
        organizations = []
        for row in rows:
            if not isinstance(row, dict) or not row.get("uid") or not row.get("label"):
                continue
            if row.get("status", "active") != "active":
                continue
            organizations.append({
                "uid": str(row["uid"]), "label": row["label"],
                "category": row.get("category"),
                "supervisorId": str(row["supervisorId"]) if row.get("supervisorId") else None,
            })
        return organizations

    def organizations_by_category(self, category="MINISTRY"):
        if category not in {"MINISTRY", "MUNICIPALITY", "REGION", "ADMINISTRATIVEREGION", "INDEPENDENTAUTHORITY"}:
            raise ValueError("Invalid organization category.")

        def fetch():
            data = self._get("organizations.json", {"status": "active", "category": category})
            return sorted(
                [row for row in self._organization_rows(data.get("organizations"))
                 if row["category"] == category], key=lambda row: row["label"],
            )

        organizations, stale = self._cached(
            ("organizations", category), ORGANIZATIONS_CACHE_SECONDS, fetch,
        )
        return {"organizations": organizations, "stale": stale}

    def organization(self, org):
        def fetch():
            row = self._get(f"organizations/{org}.json")
            if str(row.get("uid")) != org or not row.get("label"):
                raise DiavgeiaError("Diavgeia returned an invalid organization.")
            if row.get("status", "active") != "active":
                raise ValueError("Unknown active organization.")
            return self._organization_rows([row])[0]
        return self._cached(("organization", org), ORGANIZATIONS_CACHE_SECONDS, fetch)

    def supervised_organizations(self, org):
        return self._cached(
            ("supervised", org), ORGANIZATIONS_CACHE_SECONDS,
            lambda: self._organization_rows(
                self._get(f"organizations/{org}/supervised.json", {"status": "active"}).get("organizations")
            ),
        )

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

    def special_fields(self, decision_type):
        if not isinstance(decision_type, str) or not re.fullmatch(r"[\w.-]{1,40}", decision_type):
            raise ValueError("Invalid decision type.")

        def fetch():
            encoded = quote(decision_type, safe="")
            details = self._get(f"types/{encoded}/details.json")
            terms = self._get(f"types/{encoded}/terms.json").get("terms")
            if not isinstance(details.get("extraFields"), list) or not isinstance(terms, list):
                raise DiavgeiaError("Invalid special filter options.")
            labels = {row["term"]: row.get("label", row["term"]) for row in terms if isinstance(row, dict) and row.get("term")}
            fields = {}

            def visit(rows):
                for row in rows:
                    term = row.get("searchTerm")
                    if term in labels and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", term):
                        fields[term] = {"term": term, "label": labels[term],
                                        "type": row.get("type", "string"),
                                        "dictionary": row.get("dictionary"),
                                        "options": row.get("fixedValueList") or []}
                    visit(row.get("nestedFields") or [])
            visit(details["extraFields"])
            return list(fields.values())
        fields, stale = self._cached(("special", decision_type), ORGANIZATIONS_CACHE_SECONDS, fetch)
        return {"fields": fields, "stale": stale}

    def dictionary(self, name):
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,60}", name):
            raise ValueError("Invalid dictionary ID.")
        def fetch():
            items = self._get(f"dictionaries/{name}.json").get("items")
            if not isinstance(items, list):
                raise DiavgeiaError("Invalid dictionary options.")
            return [{"uid": str(row["uid"]), "label": row["label"]}
                    for row in items if isinstance(row, dict) and row.get("uid") and row.get("label")]
        items, stale = self._cached(("dictionary", name), ORGANIZATIONS_CACHE_SECONDS, fetch)
        return {"items": items, "stale": stale}

    def decisions(self, org, page=0, size=20, include_supervised=False,
                  decision_type="", thematic_category="", **search_filters):
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
        search_filters = validate_filters(search_filters)
        if search_filters["extra"] and not decision_type:
            raise ValueError("A decision type is required for special filters.")
        organization, catalog_stale = self.organization(org)
        labels = {org: organization["label"]}
        ids = {org}
        if include_supervised:
            pending = [org]
            while pending:
                children, stale = self.supervised_organizations(pending.pop())
                catalog_stale = catalog_stale or stale
                for child in children:
                    if child["uid"] not in ids:
                        ids.add(child["uid"])
                        labels[child["uid"]] = child["label"]
                        pending.append(child["uid"])

        def fetch():
            params = {
                "org": ";".join(sorted(ids)), "page": page, "size": size,
                "sort": "recent", "status": search_filters["status"],
            }
            if decision_type:
                params["type"] = decision_type
            if thematic_category:
                params["tag"] = thematic_category
            for name in ("term", "ada", "protocol"):
                if search_filters.get(name):
                    params[name] = search_filters[name]
            if search_filters.get("issue_from") or search_filters.get("updated_from") or search_filters["extra"]:
                fields = self.special_fields(decision_type)["fields"] if search_filters["extra"] else []
                query = advanced_query(params, search_filters, fields)
                data = self._get("search/advanced.json", {"q": query, "page": page, "size": size, "sort": "recent"})
            else:
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
                    "status": row.get("status", "PUBLISHED"),
                    "documentUrl": document_url(ada),
                })
            if rows and not decisions:
                raise DiavgeiaError("Diavgeia returned unusable search results.")
            return {
                "decisions": decisions, "page": page, "size": size, "total": total,
                "hasMore": bool(rows) and (page + 1) * size < total,
            }
        result, stale = self._cached(
            ("decisions", tuple(sorted(ids)), page, size, decision_type, thematic_category,
             json.dumps(search_filters, sort_keys=True, ensure_ascii=False)),
            DECISIONS_CACHE_SECONDS, fetch,
        )
        result["stale"] = stale or catalog_stale
        return result


diavgeia = DiavgeiaClient()
