import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import elections
from routers.elections import router


app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_catalog_cache():
    elections._reset_election_catalog_cache()
    yield
    elections._reset_election_catalog_cache()


def test_lists_upcoming_elections(monkeypatch):
    monkeypatch.setattr("routers.elections.list_elections_with_status", lambda: [
        {"id": "2000", "name": "VIP Test Election", "electionDay": "2031-12-06", "ocdDivisionId": "ocd-division/country:us"},
        {"id": "9000", "name": "State General Election", "electionDay": "2026-11-03", "ocdDivisionId": "ocd-division/country:us/state:md"},
    ])
    response = client.get("/elections")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0] == {
        "id": "9000", "name": "State General Election", "election_day": "2026-11-03",
        "division_id": "ocd-division/country:us/state:md",
    }
    assert response.json()["availability"]["status"] == "available"
    assert response.json()["availability"]["fetched_at"]
    assert response.json()["source"]["official_only"] is True


def test_catalog_refresh_is_cached_and_provider_failure_is_distinct(monkeypatch):
    calls = []
    monkeypatch.setattr("routers.elections.list_elections_with_status", lambda: calls.append(True) or [])
    assert client.get("/elections").status_code == 200
    assert client.get("/elections").status_code == 200
    assert len(calls) == 1

    elections._reset_election_catalog_cache()
    monkeypatch.setattr("routers.elections.list_elections_with_status", lambda: None)
    response = client.get("/elections")
    assert response.status_code == 503
    assert "Coverage could not be checked" in response.json()["detail"]


def test_catalog_serves_labeled_stale_copy_when_refresh_fails(monkeypatch):
    monkeypatch.setattr("routers.elections.list_elections_with_status", lambda: [{
        "id": "9000", "name": "State General Election", "electionDay": "2026-11-03",
        "ocdDivisionId": "ocd-division/country:us/state:md",
    }])
    assert client.get("/elections").json()["availability"]["status"] == "available"
    elections._catalog_cache["refresh_at"] = 0
    monkeypatch.setattr("routers.elections.list_elections_with_status", lambda: None)
    response = client.get("/elections")
    assert response.status_code == 200
    assert response.json()["availability"]["status"] == "stale"
    assert response.json()["items"][0]["id"] == "9000"
    assert elections._catalog_cache["refresh_at"] > 0
    assert client.get("/elections").json()["availability"]["status"] == "stale"


def test_lookup_is_official_only_and_never_echoes_registered_address(monkeypatch):
    observed = {}

    def fake_lookup(address, election_id, official_only=True):
        observed.update(address=address, election_id=election_id, official_only=official_only)
        return {
            "election": {"id": "9000", "name": "General Election", "electionDay": "2026-11-03"},
            "pollingLocations": [{
                "address": {"locationName": "Community Center", "line1": "10 Civic Way", "city": "Town", "state": "MD", "zip": "20000"},
                "pollingHours": "7 a.m. to 8 p.m.", "sources": [{"name": "County Board", "official": True}],
            }],
            "contests": [{"type": "General", "office": "Mayor", "candidates": [{"name": "Alex Example", "party": "Independent"}]}],
            "state": [{"name": "Maryland", "electionAdministrationBody": {"name": "State Board", "electionInfoUrl": "https://elections.maryland.gov/"}}],
        }

    monkeypatch.setattr("routers.elections.lookup_voter_info", fake_lookup)
    response = client.post("/elections/lookup", json={"address": " 123 Private Home Road ", "election_id": "9000"})
    assert response.status_code == 200
    payload = response.json()
    assert response.headers["cache-control"] == "no-store"
    assert observed == {"address": "123 Private Home Road", "election_id": "9000", "official_only": True}
    assert "123 Private Home Road" not in str(payload)
    assert payload["privacy"] == {
        "address_retained": False, "registration_status_collected": False, "ballot_choices_collected": False,
    }
    assert payload["contests"][0]["candidates"][0]["name"] == "Alex Example"


def test_lookup_rejects_blank_address_and_handles_no_supported_election(monkeypatch):
    assert client.post("/elections/lookup", json={"address": "          "}).status_code == 422
    monkeypatch.setattr("routers.elections.lookup_voter_info", lambda *_args, **_kwargs: None)
    assert client.post("/elections/lookup", json={"address": "123 Main Street"}).status_code == 404
