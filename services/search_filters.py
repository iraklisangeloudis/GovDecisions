"""Validation and query construction for the public search controls."""

from datetime import date
from decimal import Decimal, InvalidOperation
import json
import re

STATUSES = {"published": "Αναρτημένη", "revoked": "Ανακληθείσα",
            "pending_revocation": "Εν αναμονή ανάκλησης", "all": None}
TEXT_FIELDS = ("term", "ada", "protocol")
DATE_FIELDS = ("issue_from", "issue_to", "updated_from", "updated_to")


def validate_filters(values):
    clean = {}
    for name in TEXT_FIELDS:
        value = values.get(name, "")
        if not isinstance(value, str) or len(value) > 300 or any(ord(c) < 32 for c in value):
            raise ValueError(f"Invalid {name} filter.")
        if value.strip():
            clean[name] = value.strip()
    status = values.get("status", "published")
    if status not in STATUSES:
        raise ValueError("Invalid decision status.")
    clean["status"] = status
    for name in DATE_FIELDS:
        value = values.get(name, "")
        if not isinstance(value, str):
            raise ValueError(f"Invalid {name} date.")
        if value:
            try:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    raise ValueError()
                date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError(f"Invalid {name} date.") from exc
            clean[name] = value
    for prefix in ("issue", "updated"):
        start, end = clean.get(prefix + "_from"), clean.get(prefix + "_to")
        if bool(start) != bool(end):
            raise ValueError("Both dates are required for a date range.")
        if start and start > end:
            raise ValueError("The start date must precede the end date.")
        if start and prefix == "issue" and (date.fromisoformat(end) - date.fromisoformat(start)).days > 179:
            raise ValueError("The issue date range may contain at most 180 calendar days.")
    extras = values.get("extra", {})
    if not isinstance(extras, dict) or len(extras) > 40:
        raise ValueError("Invalid special filters.")
    clean["extra"] = extras
    return clean


def number(value):
    if not isinstance(value, str) or not re.fullmatch(r"-?\d{1,16}(?:\.\d{1,6})?", value):
        raise ValueError("Invalid numeric special filter.")
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("Invalid number.") from exc


def quote(value):
    return json.dumps(str(value), ensure_ascii=False)


def advanced_query(params, filters, extra_fields):
    parts = ["organizationUid:[" + ",".join(quote(uid) for uid in params["org"].split(";")) + "]"]
    mapping = {"type": "decisionTypeUid", "tag": "thematicCategoryUid", "term": "q",
               "ada": "ada", "protocol": "protocolNumber"}
    for name, field in mapping.items():
        if params.get(name):
            parts.append(f"{field}:{quote(params[name])}")
    if STATUSES[filters["status"]]:
        parts.append("status:" + quote(STATUSES[filters["status"]]))
    if filters.get("issue_from"):
        start, end = filters["issue_from"], filters["issue_to"]
        parts.append(f"issueDate:[DT({start}T00:00:00) TO DT({end}T23:59:59)]")
    if filters.get("updated_from"):
        parts.append(f"submissionTimestamp:[DT({filters['updated_from']}T00:00:00) TO DT({filters['updated_to']}T23:59:59)]")
    allowed = {field["term"]: field for field in extra_fields}
    for term, value in sorted(filters["extra"].items()):
        if term not in allowed:
            raise ValueError("Unknown special filter for this decision type.")
        field = allowed[term]
        if field["type"] == "number":
            if not isinstance(value, dict) or set(value) - {"min", "max"}:
                raise ValueError("Invalid numeric range.")
            lower, upper = value.get("min", ""), value.get("max", "")
            if not lower and not upper:
                continue
            low = number(lower) if lower else Decimal('-9999999999999999')
            high = number(upper) if upper else Decimal('9999999999999999')
            if low > high:
                raise ValueError("Invalid numeric range.")
            parts.append(f"{term}:[{low:f} TO {high:f}]")
        else:
            if not isinstance(value, str) or len(value) > 300 or any(ord(c) < 32 for c in value):
                raise ValueError("Invalid special filter value.")
            if not value.strip():
                continue
            if field.get("options") and value not in field["options"]:
                raise ValueError("Invalid special filter option.")
            if field["type"] == "boolean" and value not in {"true", "false"}:
                raise ValueError("Invalid boolean filter.")
            parts.append(f"{term}:{quote(value.strip())}")
    return " AND ".join(parts)
