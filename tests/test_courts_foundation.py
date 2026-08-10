from datetime import date, datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.court_models import BillCourtCase, CourtCase, CourtCaseParty, CourtEvent, IssueCourtCase
from models.database import Base, Bill, SourceDocument, get_db
from models.issue_models import Issue
from routers.courts import router


def _environment():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    app = FastAPI()
    app.include_router(router)

    def override_db():
        with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    return TestClient(app, raise_server_exceptions=False), Session


def _seed(Session):
    with Session() as session:
        source = SourceDocument(url="https://www.courtlistener.com/docket/example", publisher="CourtListener", retrieved_at=datetime(2026, 8, 9, tzinfo=timezone.utc))
        issue = Issue(slug="housing-rent", title="Housing & Rent")
        bill = Bill(bill_id="hr1-119", congress=119, bill_type="hr", bill_number=1, title="Housing Act")
        case = CourtCase(case_id="example-court-case", case_name="Tenant v. Housing Company", court_name="Example District Court", jurisdiction="federal", docket_number="1:26-cv-00001", filed_date=date(2026, 1, 2), procedural_status="pending", disposition=None, docket_url=source.url, source=source, last_verified_at=source.retrieved_at)
        session.add_all((source, issue, bill, case)); session.flush()
        session.add_all([
            CourtCaseParty(case=case, name="Tenant", role="plaintiff", entity_type="person"),
            CourtCaseParty(case=case, name="Housing Company", role="defendant", entity_type="company", entity_id="housing-company"),
            CourtEvent(case=case, event_date=date(2026, 1, 2), event_type="filing", assertion_kind="allegation", summary="The complaint alleges unlawful conduct; no finding has been made.", document_url=source.url, source=source),
            IssueCourtCase(issue_slug=issue.slug, case=case, relevance_note="The allegations concern rental housing practices.", source=source),
            BillCourtCase(bill_id=bill.bill_id, case=case, relationship_type="challenges_application", source=source),
        ])
        session.commit()


def test_case_api_keeps_allegations_procedural_and_source_backed():
    client, Session = _environment()
    _seed(Session)
    feed = client.get("/courts", params={"issue_slug": "housing-rent"}).json()
    assert feed["total"] == 1
    assert feed["items"][0]["procedural_status"] == "pending"
    detail = client.get("/courts/example-court-case").json()
    assert detail["source"]["url"].startswith("https://")
    assert detail["events"][0]["assertion_kind"] == "allegation"
    assert "no finding has been made" in detail["events"][0]["summary"]
    assert {party["role"] for party in detail["parties"]} == {"plaintiff", "defendant"}


def test_bill_filter_returns_only_explicitly_related_reviewed_cases():
    client, Session = _environment()
    _seed(Session)
    assert client.get("/courts", params={"bill_id": "hr1-119"}).json()["total"] == 1
    assert client.get("/courts", params={"bill_id": "hr999-119"}).json()["total"] == 0


def test_invalid_legal_classifications_fail_at_the_database_boundary():
    _, Session = _environment()
    with Session() as session:
        source = SourceDocument(url="https://example.uscourts.gov/docket/1", publisher="U.S. Courts", retrieved_at=datetime.now(timezone.utc))
        session.add(source); session.flush()
        session.add(CourtCase(case_id="bad-status", case_name="Example", court_name="Example Court", jurisdiction="federal", docket_number="bad", filed_date=date.today(), procedural_status="proven", docket_url=source.url, source=source, last_verified_at=source.retrieved_at))
        with pytest.raises(IntegrityError):
            session.commit()


def test_incomplete_provenance_fails_closed():
    client, Session = _environment()
    with Session() as session:
        source = SourceDocument(url="http://example.test/docket", publisher="Example", retrieved_at=datetime.now(timezone.utc))
        session.add(source); session.flush()
        session.add(CourtCase(case_id="unsafe-source", case_name="Example", court_name="Example Court", jurisdiction="state", docket_number="2", filed_date=date.today(), procedural_status="filed", docket_url="http://example.test/docket", source=source, last_verified_at=source.retrieved_at))
        session.commit()
    assert client.get("/courts/unsafe-source").status_code == 503
