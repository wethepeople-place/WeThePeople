from copy import deepcopy

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from jobs.load_discuss_fixture import DiscussFixtureValidationError, load_fixture as load_discuss
from jobs.load_housing_rent_slice import load_fixture as load_housing
from jobs.load_watch_fixture import load_fixture as load_watch
from models.auth_models import User
from models.database import Base, get_db
from models.social_models import DiscussionBlock, DiscussionPost, DiscussionReport
from routers.discussions import router
from services.jwt_auth import get_current_user, get_optional_user
from tests.test_housing_rent_loader import _fixture as housing_fixture
from tests.test_watch_slice import _watch_fixture


def _discuss_fixture():
    return {
        "threads": [{
            "author_label": "WeThePeople.place",
            "body": "What should Congress prioritize first to make rent more affordable? Start with the evidence, then explain the tradeoff behind your answer.",
            "video_id": "housing-rent-why-rents-move",
            "issue_slug": "housing-rent",
            "bill_id": "hr1-119",
            "source_url": "https://www.congress.gov/bill/119th-congress/house-bill/1",
        }]
    }


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
    return app, TestClient(app), Session


def _seed(Session):
    with Session() as session:
        load_housing(housing_fixture(), session)
        load_watch(_watch_fixture(), session)
        first = load_discuss(_discuss_fixture(), session)
        second = load_discuss(_discuss_fixture(), session)
        assert first == second == {"threads": 1, "attachments": 4}
        alice = User(email="alice@example.test", hashed_password="test", display_name="Alice")
        bob = User(email="bob@example.test", hashed_password="test", display_name="Bob")
        session.add_all((alice, bob))
        session.commit()
        return alice.id, bob.id


def _as_user(app, Session, user_id):
    def current_user():
        with Session() as session:
            return session.get(User, user_id)

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_optional_user] = current_user


def test_curated_thread_is_idempotent_paginated_and_source_backed():
    _, client, Session = _environment()
    _seed(Session)
    response = client.get("/discussions?limit=1&offset=0")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == payload["limit"] == 1
    item = payload["items"][0]
    assert item["moderation_status"] == "published"
    assert [attachment["type"] for attachment in item["attachments"]] == ["bill", "issue", "source", "video"]
    source = next(value for value in item["attachments"] if value["type"] == "source")["source"]
    assert source["url"].startswith("https://") and source["publisher"] == "Congress.gov"
    assert client.get("/discussions", params={"issue_slug": "housing-rent"}).json()["total"] == 1
    assert client.get("/discussions", params={"issue_slug": "not-reviewed"}).json()["total"] == 0
    detail = client.get(f"/discussions/{item['id']}?reply_limit=1").json()
    assert detail["reply_total"] == 0 and detail["replies"] == []
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert {"DiscussionFeedResponse", "DiscussionDetailResponse", "ReplyCreatedResponse"} <= set(schemas)


def test_hidden_content_is_not_public_and_invalid_fixture_writes_nothing():
    _, client, Session = _environment()
    _seed(Session)
    with Session() as session:
        session.add(DiscussionPost(author_label="Hidden", body="private moderation state", moderation_status="hidden"))
        session.commit()
    assert client.get("/discussions").json()["total"] == 1

    payload = deepcopy(_discuss_fixture())
    payload["threads"].append(deepcopy(payload["threads"][0]))
    with Session() as session:
        try:
            load_discuss(payload, session)
            assert False, "invalid fixture should fail"
        except DiscussFixtureValidationError:
            pass
        assert session.query(DiscussionPost).count() == 2


def test_reply_requires_auth_is_rate_limited_and_validates_parent(monkeypatch):
    app, client, Session = _environment()
    alice_id, _ = _seed(Session)
    post_id = client.get("/discussions").json()["items"][0]["id"]
    assert client.post(f"/discussions/{post_id}/replies", json={"body": "hello"}).status_code == 401

    _as_user(app, Session, alice_id)
    monkeypatch.setattr("routers.discussions.REPLY_LIMIT", 1)
    created = client.post(f"/discussions/{post_id}/replies", json={"body": "Evidence should lead the discussion."})
    assert created.status_code == 201
    assert client.post(f"/discussions/{post_id}/replies", json={"body": "Second"}).status_code == 429
    assert client.post(f"/discussions/{post_id}/replies", json={"body": "   "}).status_code in {422, 429}


def test_reports_are_private_and_blocks_filter_the_authenticated_feed():
    app, client, Session = _environment()
    alice_id, bob_id = _seed(Session)
    with Session() as session:
        bob_post = DiscussionPost(author_id=bob_id, author_label="Bob", body="Bob's published view")
        session.add(bob_post)
        session.commit()
        bob_post_id = bob_post.id

    _as_user(app, Session, alice_id)
    report = client.post("/discussions/reports", json={"target_type": "post", "target_id": bob_post_id, "reason": "other", "details": "Private context"})
    assert report.status_code == 201 and report.json() == {"status": "received"}
    assert "Private context" not in str(client.get("/discussions").json())
    assert client.post("/discussions/reports", json={"target_type": "post", "target_id": bob_post_id, "reason": "other"}).status_code == 409

    blocked = client.post(f"/discussions/blocks/{bob_id}")
    assert blocked.status_code == 201
    feed = client.get("/discussions").json()
    assert all(item["author"]["id"] != bob_id for item in feed["items"])
    with Session() as session:
        assert session.query(DiscussionReport).count() == 1
        assert session.query(DiscussionBlock).count() == 1
