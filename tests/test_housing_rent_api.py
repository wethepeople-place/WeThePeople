from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from jobs.load_housing_rent_slice import load_fixture
from models.database import Base, get_db
from routers.issues import router
from tests.test_housing_rent_loader import _fixture


def _client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    app = FastAPI()
    app.include_router(router)

    def override_db():
        with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    return TestClient(app), Session


def test_issue_api_empty_state_and_missing_issue():
    client, Session = _client()
    assert client.get("/issues/housing-rent").status_code == 404

    agenda = client.get("/issues")
    assert agenda.status_code == 200
    assert agenda.json() == {
        "total": 0,
        "methodology": {
            "kind": "initial_evidence_catalog",
            "label": "Initial agenda",
            "description": "Ordered by published source coverage, not community popularity.",
            "community_ranked": False,
            "updated_at": None,
        },
        "items": [],
    }

    with Session() as session:
        from models.issue_models import Issue

        session.add(Issue(slug="housing-rent", title="Housing & Rent"))
        session.commit()

    summary = client.get("/issues/housing-rent").json()
    assert summary["evidence_series_count"] == 0
    assert summary["bill_count"] == 0
    assert client.get("/issues/housing-rent/evidence").json() == {
        "issue_slug": "housing-rent",
        "total": 0,
        "series": [],
    }
    assert client.get("/issues/housing-rent/bills").json() == {
        "issue_slug": "housing-rent",
        "total": 0,
        "bills": [],
    }
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert {"IssueSummaryResponse", "IssueEvidenceResponse", "IssueBillsResponse"} <= set(schemas)


def test_housing_rent_api_preserves_exact_scope_identifiers_and_provenance():
    client, Session = _client()
    payload = _fixture()
    with Session() as session:
        load_fixture(payload, session)

    summary = client.get("/issues/housing-rent").json()
    evidence = client.get("/issues/housing-rent/evidence").json()
    bills = client.get("/issues/housing-rent/bills").json()

    assert summary == {
        "slug": "housing-rent",
        "title": "Housing & Rent",
        "summary": None,
        "evidence_series_count": 3,
        "bill_count": 7,
    }
    assert evidence["total"] == 3
    assert {item["key"] for item in evidence["series"]} == {"hud_fmr_2br_proxy", "rent_cpi", "avg_wage"}
    assert bills["total"] == 7
    assert {item["bill_id"] for item in bills["bills"]} == {
        "hr1-119", "hr6644-119", "s968-119", "hr6124-119",
        "s3207-119", "hr2725-119", "s1515-119",
    }
    assert {item["phase"] for item in bills["bills"]} == {"upcoming"}

    for source in [
        *(item["source"] for item in evidence["series"]),
        *(obs["source"] for item in evidence["series"] for obs in item["observations"]),
        *(item["source"] for item in bills["bills"]),
    ]:
        assert source["url"].startswith("https://")
        assert source["publisher"]
        assert datetime.fromisoformat(source["retrieved_at"]).replace(tzinfo=timezone.utc)


def test_issue_bill_api_accepts_enacted_phase():
    client, Session = _client()
    payload = _fixture()
    payload["bills"][0]["phase"] = "enacted"
    with Session() as session:
        load_fixture(payload, session)
    response = client.get("/issues/housing-rent/bills")
    assert response.status_code == 200
    assert "enacted" in {item["phase"] for item in response.json()["bills"]}


def test_issue_agenda_uses_reviewed_coverage_without_popularity_claims():
    client, Session = _client()
    with Session() as session:
        load_fixture(_fixture(), session)

    response = client.get("/issues")
    assert response.status_code == 200
    payload = response.json()
    assert payload["methodology"]["community_ranked"] is False
    assert payload["items"][0]["rank"] == 1
    assert payload["items"][0]["slug"] == "housing-rent"
    assert payload["items"][0]["evidence_series_count"] == 3
    assert payload["items"][0]["bill_count"] == 7
    assert payload["items"][0]["community_score"] is None
    assert payload["items"][0]["evidence_note"]
