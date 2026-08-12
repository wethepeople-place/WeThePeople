from routers import lookup


def test_official_house_zip_parser_handles_current_district(monkeypatch):
    class Response:
        text = '<script>var districts=["MD02"];</script>'

        def raise_for_status(self):
            return None

    monkeypatch.setattr(lookup.requests, "get", lambda *args, **kwargs: Response())
    assert lookup._official_house_districts("21136") == [("MD", 2)]


def test_live_congress_members_returns_senators_and_resolved_house_member(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            def member(bioguide, name, chamber, district=None):
                return {
                    "bioguideId": bioguide,
                    "name": name,
                    "partyName": "Democratic",
                    "district": district,
                    "terms": {"item": [{"chamber": chamber, "startYear": 2025}]},
                    "url": f"https://api.congress.gov/v3/member/{bioguide}",
                }

            return {"members": [
                member("O000176", "Olszewski, Johnny", "House of Representatives", 2),
                member("H001052", "Harris, Andy", "House of Representatives", 1),
                member("V000128", "Van Hollen, Chris", "Senate"),
                member("A000382", "Alsobrooks, Angela D.", "Senate"),
            ]}

    monkeypatch.setenv("CONGRESS_API_KEY", "test-key")
    monkeypatch.setattr(lookup.requests, "get", lambda *args, **kwargs: Response())
    members = lookup._live_congress_members("MD", {2})

    assert {(member["bioguide_id"], member["chamber"]) for member in members} == {
        ("O000176", "house"),
        ("V000128", "senate"),
        ("A000382", "senate"),
    }
    assert all(member["source"]["publisher"] == "Congress.gov" for member in members)
    assert all(member["profile_available"] is False for member in members)

    lookup._congress_member_cache.clear()
    senators = lookup._live_congress_members("MD", set())
    assert {member["bioguide_id"] for member in senators} == {"V000128", "A000382"}
    assert all(member["chamber"] == "senate" for member in senators)


def test_zip_crossing_house_districts_still_returns_senators(monkeypatch):
    class EmptyQuery:
        def filter(self, *args):
            return self

        def order_by(self, *args):
            return self

        def all(self):
            return []

    class EmptyDB:
        def query(self, *args):
            return EmptyQuery()

    senators = [
        {"person_id": "a000382", "name": "Angela D. Alsobrooks", "chamber": "senate"},
        {"person_id": "v000128", "name": "Chris Van Hollen", "chamber": "senate"},
    ]
    monkeypatch.setattr(lookup, "_zip_to_state", lambda zip_code: "MD")
    monkeypatch.setattr(lookup, "_cached_district_lookup", lambda zip_code: None)
    monkeypatch.setattr(lookup, "_official_house_districts", lambda zip_code: [])
    monkeypatch.setattr(lookup, "_live_congress_members", lambda state, districts: senators)

    response = lookup.zip_lookup("21208", EmptyDB())

    assert response["districts"] == []
    assert response["district_resolution_required"] is True
    assert response["representative_count"] == 2
    assert response["representatives"] == senators
