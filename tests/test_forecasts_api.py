from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.auth_models import User
from models.database import Base, Bill, get_db
from models.forecast_models import ForecastMarket, ForecastPrediction
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

    payload = client.get("/forecasts").json()
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
    assert restored.json()["current_user_choice"] == "candidate-a"


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
    assert first.status_code == 200
    assert first.json()["resolved_option"] == "yes"
    replacement = {**resolution, "status": "void", "resolved_option": None}
    assert client.patch(f"/forecasts/admin/{market_id}", json=replacement).status_code == 409
