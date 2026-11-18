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


def test_homepage_uses_json_and_formats_dates(client, api):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Test decision" in response.data
    assert b"01/01/1970 00:00 UTC" in response.data
    assert b"https://diavgeia.gov.gr/doc/TEST-1" in response.data
    query = api.last_request.qs
    assert query["org"] == ["6"]
    assert "type" not in query
    assert api.last_request.timeout == DIAVGEIA_TIMEOUT


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
    assert b"previously fetched" in client.get("/").data
    clock[0] = 360
    assert client.get("/api/decisions?org=6").status_code == 503
    api.get(f"{DIAVGEIA_API_URL}/search.json", json=results([decision("NEW-1")]))
    response = client.get("/api/decisions?org=6")
    assert response.json["decisions"][0]["ada"] == "NEW-1"
    assert response.json["stale"] is False
