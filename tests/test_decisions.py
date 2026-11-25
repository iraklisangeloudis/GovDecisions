import pytest
import requests

from app import app
from config import DIAVGEIA_API_URL, DIAVGEIA_TIMEOUT
from services.diavgeia import DiavgeiaClient

ORGANIZATIONS = [
    {"uid": "6", "label": "Defence", "category": "MINISTRY"},
    {"uid": "7", "label": "Child", "supervisorId": "6"},
    {"uid": "8", "label": "Grandchild", "supervisorId": "7"},
    {"uid": "10", "label": "Foreign Affairs", "category": "MINISTRY"},
]


def decision(ada="TEST-1", org="6", **fields):
    return {"ada": ada, "organizationId": org, "subject": "Test decision",
            "submissionTimestamp": 0, **fields}


def results(rows=None, total=None):
    rows = [decision()] if rows is None else rows
    return {"decisions": rows, "info": {"total": len(rows) if total is None else total}}


@pytest.fixture
def api(requests_mock, monkeypatch):
    service = DiavgeiaClient()
    monkeypatch.setattr("routes.decisions.diavgeia", service)
    requests_mock.get(f"{DIAVGEIA_API_URL}/organizations.json",
                      json={"organizations": ORGANIZATIONS})
    requests_mock.get(f"{DIAVGEIA_API_URL}/search.json", json=results())
    return requests_mock


@pytest.fixture
def client(api):
    with app.test_client() as client:
        yield client


def test_homepage_loads_without_upstream(client, api):
    response = client.get("/")
    assert response.status_code == 200
    assert b'id="sidebar"' in response.data
    assert b'id="welcome-state"' in response.data
    assert b'/static/app.js' in response.data
    assert not api.called


def test_no_selected_organization_does_not_fetch(client, api):
    assert client.get("/api/decisions").json["decisions"] == []
    assert not api.called


def test_ministries_only(client):
    response = client.get("/api/organizations")
    assert [org["uid"] for org in response.json["organizations"]] == ["6", "10"]


def test_pagination_parameters_and_end(client, api):
    api.get(f"{DIAVGEIA_API_URL}/search.json", json=results(total=21))
    assert client.get("/api/decisions?org=6").json["hasMore"] is True
    data = client.get("/api/decisions?org=6&page=1&size=20").json
    assert data["page"] == 1
    assert data["total"] == 21
    assert data["hasMore"] is False
    assert api.last_request.qs["page"] == ["1"]
    assert api.last_request.qs["org"] == ["6"]
    assert "type" not in api.last_request.qs
    assert api.last_request.timeout == DIAVGEIA_TIMEOUT


def test_empty_page_stops_pagination(client, api):
    api.get(f"{DIAVGEIA_API_URL}/search.json", json=results([], total=100))
    data = client.get("/api/decisions?org=6").json
    assert data["decisions"] == []
    assert data["hasMore"] is False


def test_supervised_includes_nested_organizations(client, api):
    api.get(f"{DIAVGEIA_API_URL}/search.json", json=results([decision(org="8")]))
    data = client.get("/api/decisions?org=6&include_supervised=true").json
    assert set(api.last_request.qs["org"][0].split(";")) == {"6", "7", "8"}
    assert data["decisions"][0]["organizationLabel"] == "Grandchild"


@pytest.mark.parametrize("query", [
    "org=invalid", "org=6&page=-1", "org=6&include_supervised=yes",
])
def test_invalid_query_is_rejected_before_network(client, api, query):
    assert client.get("/api/decisions?" + query).status_code == 400
    assert not api.called


@pytest.mark.parametrize("failure", [
    {"exc": requests.Timeout}, {"status_code": 503}, {"text": "not json"},
])
def test_upstream_failures_are_not_empty_successes(client, api, failure):
    api.get(f"{DIAVGEIA_API_URL}/search.json", **failure)
    response = client.get("/api/decisions?org=6")
    assert response.status_code == 503
    assert "error" in response.json


def test_missing_fields_and_duplicates(client, api):
    rows = [None, {}, decision(), decision(), decision("TEST-2", subject=None),
            decision("OTHER-1", org="10")]
    api.get(f"{DIAVGEIA_API_URL}/search.json", json=results(rows))
    response = client.get("/api/decisions?org=6")
    assert response.status_code == 200
    assert [d["ada"] for d in response.json["decisions"]] == ["TEST-1", "TEST-2"]
    assert response.json["decisions"][1]["subject"] == "—"


def test_pdf_does_not_depend_on_page_one(client, api):
    response = client.get("/download/OTHER-PAGE")
    assert response.status_code == 302
    assert response.location == "https://diavgeia.gov.gr/doc/OTHER-PAGE"
    assert not api.called


def test_cache_isolated_by_query(client, api):
    for query in ["org=6", "org=6", "org=10", "org=6&page=1", "org=6&size=10",
                  "org=6&include_supervised=true"]:
        # Use a valid row for each requested scope.
        org = "10" if query == "org=10" else "6"
        api.get(f"{DIAVGEIA_API_URL}/search.json", json=results([decision(org=org)]))
        assert client.get("/api/decisions?" + query).status_code == 200
    assert len(api.request_history) == 6  # one catalog plus five searches


def test_cache_refresh_and_stale_expiry(client, api, monkeypatch):
    clock = [0]
    monkeypatch.setattr("services.diavgeia.monotonic", lambda: clock[0])
    assert client.get("/api/decisions?org=6").json["stale"] is False
    clock[0] = 179
    assert client.get("/api/decisions?org=6").status_code == 200
    assert len(api.request_history) == 2
    clock[0] = 180
    api.get(f"{DIAVGEIA_API_URL}/search.json", exc=requests.Timeout)
    response = client.get("/api/decisions?org=6")
    assert response.status_code == 200
    assert response.json["stale"] is True
    assert response.json["decisions"][0]["ada"] == "TEST-1"
    clock[0] = 360
    assert client.get("/api/decisions?org=6").status_code == 503
    api.get(f"{DIAVGEIA_API_URL}/search.json", json=results([decision("NEW-1")]))
    response = client.get("/api/decisions?org=6")
    assert response.json["decisions"][0]["ada"] == "NEW-1"
    assert response.json["stale"] is False


def test_filter_options_are_selectable_and_cached(client, api):
    api.get(f"{DIAVGEIA_API_URL}/types.json", json={"decisionTypes": [
        {"uid": "group", "label": "Group", "allowedInDecisions": False},
        {"uid": "A.1", "label": "Type A", "allowedInDecisions": True},
    ]})
    api.get(f"{DIAVGEIA_API_URL}/dictionaries/THK.json",
            json={"items": [{"uid": "20", "label": "Theme"}]})
    for _ in range(2):
        data = client.get("/api/filters").json
        assert data["decisionTypes"] == [{"uid": "A.1", "label": "Type A"}]
        assert data["thematicCategories"][0]["uid"] == "20"
    assert len(api.request_history) == 2


def test_filters_reach_upstream_and_have_separate_cache(client, api):
    for suffix in ["&type=A.1&tag=20", "&type=A.1&tag=20", "&type=A.2&tag=20", ""]:
        response = client.get("/api/decisions?org=6" + suffix)
        assert response.status_code == 200
        if suffix:
            assert api.last_request.qs["tag"] == ["20"]
            assert api.last_request.qs["type"] == ["a.2" if "A.2" in suffix else "a.1"]
    assert len(api.request_history) == 4  # catalog and three distinct searches


def test_invalid_filter_is_rejected(client, api):
    assert client.get("/api/decisions?org=6&type=A;B").status_code == 400
    assert not api.called


def test_preview_serves_inline_pdf(client, api):
    content = b"%PDF-1.4\nexample"
    api.get("https://diavgeia.gov.gr/doc/TEST-1", content=content,
            headers={"Content-Type": "application/pdf", "Content-Disposition": "attachment"})
    response = client.get("/document/TEST-1")
    assert response.status_code == 200
    assert response.data == content
    assert response.content_type == "application/pdf"
    assert response.headers["Content-Disposition"].startswith("inline;")
    assert response.headers["Cache-Control"] == "private, no-store"
    response.close()


@pytest.mark.parametrize("upstream, expected", [
    ({"status_code": 404}, 404),
    ({"exc": requests.Timeout}, 503),
    ({"content": b"not a pdf", "headers": {"Content-Type": "application/pdf"}}, 502),
])
def test_preview_errors_are_reported(client, api, upstream, expected):
    api.get("https://diavgeia.gov.gr/doc/TEST-1", **upstream)
    assert client.get("/document/TEST-1").status_code == expected


def test_preview_size_limit_without_content_length(client, api, monkeypatch):
    monkeypatch.setattr("services.documents.MAX_PDF_BYTES", 8)
    api.get("https://diavgeia.gov.gr/doc/TEST-1", content=b"%PDF-1.4 oversized",
            headers={"Content-Type": "application/pdf"})
    assert client.get("/document/TEST-1").status_code == 413


def test_common_search_filters_reach_upstream(client, api):
    response = client.get("/api/decisions", query_string={
        "org": "6", "term": "budget", "ada": "TEST-1",
        "protocol": "123", "status": "all",
    })
    assert response.status_code == 200
    for name, value in {"term": "budget", "ada": "test-1",
                        "protocol": "123", "status": "all"}.items():
        assert api.last_request.qs[name] == [value]


def test_historical_dates_use_inclusive_advanced_query(client, api):
    api.get(f"{DIAVGEIA_API_URL}/search/advanced.json", json=results())
    response = client.get("/api/decisions?org=6&issue_from=2020-01-01&issue_to=2020-01-31&updated_from=2020-02-01&updated_to=2020-02-29")
    assert response.status_code == 200
    query = api.last_request.qs["q"][0]
    assert "issuedate:[dt(2020-01-01t00:00:00) to dt(2020-01-31t23:59:59)]" in query
    assert "submissiontimestamp:[dt(2020-02-01t00:00:00) to dt(2020-02-29t23:59:59)]" in query


@pytest.mark.parametrize("query", [
    "issue_from=2020-01-01&issue_to=2020-12-31", "updated_from=2020-01-01", "status=invalid",
])
def test_invalid_advanced_filters_fail_before_network(client, api, query):
    assert client.get("/api/decisions?org=6&" + query).status_code == 400
    assert not api.called


def test_special_amounts_are_validated_and_added_to_query(client, api):
    import json
    api.get(f"{DIAVGEIA_API_URL}/types/A.1/details.json", json={"extraFields": [{
        "type": "object", "nestedFields": [{"searchTerm": "amount", "type": "number"}]
    }]})
    api.get(f"{DIAVGEIA_API_URL}/types/A.1/terms.json", json={"terms": [{"term": "amount", "label": "Amount"}]})
    api.get(f"{DIAVGEIA_API_URL}/search/advanced.json", json=results())
    response = client.get("/api/decisions", query_string={"org": "6", "type": "A.1", "extra": json.dumps({"amount": {"min": "100", "max": "5000"}})})
    assert response.status_code == 200
    assert "amount:[100 to 5000]" in api.last_request.qs["q"][0]
    assert "issuedate:" not in api.last_request.qs["q"][0]
    response = client.get("/api/decisions", query_string={"org": "6", "type": "A.1", "extra": json.dumps({"unrecognizedField": "value"})})
    assert response.status_code == 400


def test_special_strings_cannot_inject_query_terms(client, api):
    import json
    api.get(f"{DIAVGEIA_API_URL}/types/A.1/details.json", json={"extraFields": [{"searchTerm": "receiverName", "type": "string"}]})
    api.get(f"{DIAVGEIA_API_URL}/types/A.1/terms.json", json={"terms": [{"term": "receiverName", "label": "Name"}]})
    api.get(f"{DIAVGEIA_API_URL}/search/advanced.json", json=results())
    value = 'name" OR status:"revoked'
    response = client.get("/api/decisions", query_string={"org": "6", "type": "A.1", "extra": json.dumps({"receiverName": value})})
    assert response.status_code == 200
    assert ('receiverName:' + json.dumps(value)).lower() in api.last_request.qs["q"][0]
