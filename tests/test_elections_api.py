from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.elections import router


app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_lists_upcoming_elections(monkeypatch):
    monkeypatch.setattr("routers.elections.list_elections", lambda: [{
        "id": "9000", "name": "State General Election", "electionDay": "2026-11-03",
        "ocdDivisionId": "ocd-division/country:us/state:md",
    }])
    response = client.get("/elections")
    assert response.status_code == 200
    assert response.json()["items"][0] == {
        "id": "9000", "name": "State General Election", "election_day": "2026-11-03",
        "division_id": "ocd-division/country:us/state:md",
    }


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
