from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.auth_models import User
from models.database import Base, Bill, get_db
from models.forecast_models import ForecastMarket, ForecastPrediction, ForecastResolutionReceipt
from jobs.forecast_retention import expire_forecast_predictions
from routers.forecasts import router
from services.forecast_tokens import sign_election_contest
from services.jwt_auth import get_current_user, get_optional_user


def _environment():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    app = FastAPI(); app.include_router(router)

    def override_db():
        with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    return app, TestClient(app), Session


def _seed(Session):
    with Session() as session:
        users = [User(email=f"u{i}@example.test", hashed_password="test", display_name=f"User {i}") for i in range(6)]
        users[-1].role = "admin"
        users[-2].role = "admin"
        bill = Bill(bill_id="hr42-119", congress=119, bill_type="hr", bill_number=42, title="Test Act")
        session.add_all([*users, bill]); session.commit()
        return [user.id for user in users]


def _as_user(app, Session, user_id):
    def current_user():
        with Session() as session:
            return session.get(User, user_id)
    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_optional_user] = current_user


def test_bill_forecast_requires_sign_in_and_has_no_money_contract():
    app, client, Session = _environment(); user_ids = _seed(Session)
    assert client.put("/forecasts/bills/hr42-119", json={"option_key": "yes"}).status_code == 401
    _as_user(app, Session, user_ids[0])
    response = client.put("/forecasts/bills/hr42-119", json={"option_key": "yes"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization, Cookie"
    payload = response.json()
    assert payload["current_user_choice"] == "yes"
    assert payload["response_count"] is None
    assert "No money" in payload["rules"]
    assert {item["key"] for item in payload["options"]} == {"yes", "no"}


def test_one_changeable_prediction_and_privacy_threshold():
    app, client, Session = _environment(); user_ids = _seed(Session)
    for index, user_id in enumerate(user_ids[:5]):
        _as_user(app, Session, user_id)
        choice = "no" if index == 0 else "yes"
        assert client.put("/forecasts/bills/hr42-119", json={"option_key": choice}).status_code == 200
    payload = client.get("/forecasts/bills/hr42-119").json()
    assert payload["response_count"] == 5
    assert {item["key"]: item["responses"] for item in payload["options"]} == {"yes": 4, "no": 1}
    _as_user(app, Session, user_ids[0])
    client.put("/forecasts/bills/hr42-119", json={"option_key": "yes"})
    with Session() as session:
        market = session.query(ForecastMarket).one()
        assert session.query(ForecastPrediction).filter_by(market_id=market.id).count() == 5


def test_open_forecast_discovery_is_privacy_safe_and_does_not_create_markets():
    app, client, Session = _environment(); user_ids = _seed(Session)
    _as_user(app, Session, user_ids[0])
    assert client.put("/forecasts/bills/hr42-119", json={"option_key": "yes"}).status_code == 200
    app.dependency_overrides.pop(get_optional_user)

    discovery = client.get("/forecasts")
    assert discovery.headers["cache-control"] == "private, no-store"
    assert discovery.headers["vary"] == "Authorization, Cookie"
    payload = discovery.json()
    assert payload["privacy_threshold"] == 5
    assert len(payload["items"]) == 1
    market = payload["items"][0]
    assert market["market_type"] == "bill"
    assert market["subject_id"] == "hr42-119"
    assert market["current_user_choice"] is None
    assert market["response_count"] is None
    assert all(option["responses"] is None and option["share"] is None for option in market["options"])
    assert "user_id" not in str(payload)
    with Session() as session:
        assert session.query(ForecastMarket).count() == 1
        assert session.query(ForecastPrediction).count() == 1

    assert client.get("/forecasts?market_type=election").json()["items"] == []


def test_election_forecast_accepts_only_signed_official_contest():
    app, client, Session = _environment(); user_ids = _seed(Session); _as_user(app, Session, user_ids[0])
    token = sign_election_contest({
        "election_id": "9000", "office": "U.S. Representative", "district": "District 1",
        "options": [{"key": "candidate-a", "label": "Candidate A"}, {"key": "candidate-b", "label": "Candidate B"}],
        "closes_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "source_url": "https://elections.example.gov/results",
    })
    assert client.put("/forecasts/elections", json={"contest_token": "not-signed", "option_key": "candidate-a"}).status_code == 422
    response = client.put("/forecasts/elections", json={"contest_token": token, "option_key": "candidate-a"})
    assert response.status_code == 200
    assert response.json()["market_type"] == "election"
    assert response.json()["source_url"] == "https://elections.example.gov/results"
    restored = client.post("/forecasts/elections/market", json={"contest_token": token})
    assert restored.status_code == 200
    assert restored.headers["cache-control"] == "private, no-store"
    assert restored.json()["current_user_choice"] == "candidate-a"


def test_synthetic_demo_accounts_cannot_create_forecast_activity():
    app, client, Session = _environment(); _seed(Session)
    with Session() as session:
        demo = User(
            email="demo.discussion.test01@example.invalid",
            hashed_password="synthetic-demo-no-login",
            display_name="Test User 01 (Demo)",
        )
        session.add(demo); session.commit(); demo_id = demo.id
    _as_user(app, Session, demo_id)
    response = client.put("/forecasts/bills/hr42-119", json={"option_key": "yes"})
    assert response.status_code == 403
    with Session() as session:
        assert session.query(ForecastMarket).count() == 0
        assert session.query(ForecastPrediction).count() == 0


def test_final_resolution_is_official_sourced_and_immutable():
    app, client, Session = _environment(); user_ids = _seed(Session)
    _as_user(app, Session, user_ids[0])
    market_id = client.put("/forecasts/bills/hr42-119", json={"option_key": "yes"}).json()["id"]
    _as_user(app, Session, user_ids[-1])
    resolution = {
        "status": "resolved", "resolved_option": "yes",
        "source_url": "https://www.congress.gov/bill/119th-congress/house-bill/42",
        "reason": "Congress.gov records that the measure became law.",
    }
    first = client.patch(f"/forecasts/admin/{market_id}", json=resolution)
    assert first.status_code == 201
    proposal_id = first.json()["id"]
    assert first.json()["review_status"] == "pending"
    assert client.post(
        f"/forecasts/admin/resolution-proposals/{proposal_id}/review",
        json={"decision": "approved", "reason": "Independent review confirms the official source and criteria."},
    ).status_code == 403
    _as_user(app, Session, user_ids[-2])
    approved = client.post(
        f"/forecasts/admin/resolution-proposals/{proposal_id}/review",
        json={"decision": "approved", "reason": "Independent review confirms the official source and criteria."},
    )
    assert approved.status_code == 200
    assert approved.json()["market"]["resolved_option"] == "yes"
    assert approved.json()["market"]["resolution_reason"] == resolution["reason"]
    assert approved.json()["market"]["resolved_at"] is not None
    with Session() as session:
        assert session.query(ForecastResolutionReceipt).filter_by(market_id=market_id).count() == 1
    replacement = {**resolution, "status": "void", "resolved_option": None}
    assert client.patch(f"/forecasts/admin/{market_id}", json=replacement).status_code == 409


def test_resolution_rejects_non_authoritative_source_hosts():
    app, client, Session = _environment(); user_ids = _seed(Session)
    _as_user(app, Session, user_ids[0])
    market_id = client.put("/forecasts/bills/hr42-119", json={"option_key": "yes"}).json()["id"]
    _as_user(app, Session, user_ids[-1])
    response = client.patch(f"/forecasts/admin/{market_id}", json={
        "status": "resolved", "resolved_option": "yes",
        "source_url": "https://social.example/claim",
        "reason": "An unapproved source cannot finalize a civic Forecast.",
    })
    assert response.status_code == 422


def test_retention_is_dry_run_by_default_and_requires_receipt():
    app, client, Session = _environment(); user_ids = _seed(Session)
    _as_user(app, Session, user_ids[0])
    market_id = client.put("/forecasts/bills/hr42-119", json={"option_key": "yes"}).json()["id"]
    with Session() as session:
        market = session.get(ForecastMarket, market_id)
        market.status = "resolved"; market.resolved_option = "yes"
        market.resolved_at = datetime.now(timezone.utc) - timedelta(days=366)
        session.commit()
        assert expire_forecast_predictions(session)["identifiable_choices"] == 0
        assert session.query(ForecastPrediction).count() == 1
        session.add(ForecastResolutionReceipt(
            market_id=market_id, proposal_id=999, sequence=1, status="resolved",
            resolved_option="yes", source_url=market.source_url, reason="Official outcome retained as aggregate evidence.",
        ))
        # SQLite test FK enforcement is intentionally off; production FK remains enforced.
        session.commit()
        assert expire_forecast_predictions(session)["identifiable_choices"] == 1
        assert expire_forecast_predictions(session, apply=True)["deleted"] == 1
        assert session.query(ForecastPrediction).count() == 0


def test_reviewed_promise_requires_independent_admin_and_stays_disabled(monkeypatch):
    monkeypatch.delenv("WTP_ENABLE_REVIEWED_PROMISE_FORECASTS", raising=False)
    app, client, Session = _environment(); user_ids = _seed(Session)
    _as_user(app, Session, user_ids[-1])
    payload = {
        "person_id": "person-1", "person_name": "Public Official", "office": "Governor",
        "exact_quote": "I will sign the published clean-water bill before the end of 2028.",
        "source_url": "https://governor.example.gov/transcript/clean-water",
        "promise_date": "2026-08-01T12:00:00Z", "jurisdiction": "Example State",
        "government_level": "state", "deadline": "2028-12-31T23:59:59Z",
        "measurable_criteria": "The named official signs the identified clean-water bill into law by the deadline.",
        "evidence_plan": "Use the enrolled-bill record and signed legislation page maintained by the state government.",
        "template_version": "1.0",
    }
    created = client.post("/forecasts/admin/reviewed-promises", json=payload)
    assert created.status_code == 201
    promise_id = created.json()["id"]
    review = {"decision": "approved", "reason": "The quote, deadline, criteria, and official evidence plan are independently verified."}
    assert client.post(f"/forecasts/admin/reviewed-promises/{promise_id}/review", json=review).status_code == 403
    _as_user(app, Session, user_ids[-2])
    approved = client.post(f"/forecasts/admin/reviewed-promises/{promise_id}/review", json=review)
    assert approved.status_code == 200
    assert approved.json()["forecast_feature_enabled"] is False
    public = client.get("/forecasts/reviewed-promises").json()
    assert public["forecast_feature_enabled"] is False
    assert public["items"][0]["exact_quote"] == payload["exact_quote"]
    assert "reviewed_by_user_id" not in str(public)


def test_correction_preserves_original_receipt_and_requires_second_admin():
    app, client, Session = _environment(); user_ids = _seed(Session)
    _as_user(app, Session, user_ids[0])
    market_id = client.put("/forecasts/bills/hr42-119", json={"option_key": "yes"}).json()["id"]
    initial = {"status": "resolved", "resolved_option": "yes",
               "source_url": "https://www.congress.gov/bill/119th-congress/house-bill/42",
               "reason": "Congress.gov initially recorded that the measure became law."}
    _as_user(app, Session, user_ids[-1])
    proposal_id = client.patch(f"/forecasts/admin/{market_id}", json=initial).json()["id"]
    _as_user(app, Session, user_ids[-2])
    assert client.post(f"/forecasts/admin/resolution-proposals/{proposal_id}/review", json={
        "decision": "approved", "reason": "Independent review confirms the initial official record."
    }).status_code == 200
    correction = {"status": "void", "resolved_option": None,
                  "source_url": "https://www.congress.gov/bill/119th-congress/house-bill/42",
                  "reason": "Congress.gov corrected the record; the forecast criteria can no longer be resolved reliably."}
    correction_id = client.post(f"/forecasts/admin/{market_id}/correction-proposals", json=correction).json()["id"]
    assert client.post(f"/forecasts/admin/resolution-proposals/{correction_id}/review", json={
        "decision": "approved", "reason": "The proposing administrator cannot approve the correction."
    }).status_code == 403
    _as_user(app, Session, user_ids[-1])
    approved = client.post(f"/forecasts/admin/resolution-proposals/{correction_id}/review", json={
        "decision": "approved", "reason": "Independent review confirms the corrected authoritative record."
    })
    assert approved.status_code == 200
    receipts = client.get(f"/forecasts/{market_id}/receipts").json()["receipts"]
    assert [r["sequence"] for r in receipts] == [1, 2]
    assert receipts[0]["status"] == "resolved" and receipts[1]["status"] == "void"
    assert receipts[1]["supersedes_sequence"] == 1
