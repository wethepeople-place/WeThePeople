from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from jobs.load_housing_rent_slice import load_fixture as load_housing
from jobs.load_watch_fixture import WatchFixtureValidationError, load_fixture, validate_fixture
from models.database import Base, get_db
from models.auth_models import User
from models.issue_models import Video, VideoBill, VideoIssue, VideoLike, VideoSave
from models.social_models import DiscussionAttachment, DiscussionPost, DiscussionReply
from routers.videos import router
from services.jwt_auth import get_current_user, get_optional_user
from tests.test_housing_rent_loader import _fixture as housing_fixture


def _watch_fixture():
    return {
        "videos": [{
            "video_id": "housing-rent-why-rents-move",
            "creator_label": "WeThePeople.place",
            "caption": "Start with official housing evidence.",
            "transcript": "Inspect the evidence and related bill.",
            "captions_url": None,
            "media_url": "https://example.gov/video.mp4",
            "published_at": "2026-07-31T00:00:00Z",
            "issue_slug": "housing-rent",
            "bill_ids": ["hr1-119"],
            "source": {
                "url": "https://www.congress.gov/bill/119th-congress/house-bill/1",
                "publisher": "Congress.gov",
                "retrieved_at": "2026-07-31T00:00:00Z",
            },
        }]
    }


def _client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'watch.db'}", connect_args={"check_same_thread": False}
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


def test_watch_empty_missing_and_openapi(tmp_path):
    client, _ = _client(tmp_path)
    assert client.get("/videos").json() == {"total": 0, "videos": [], "next_cursor": None, "has_more": False}
    assert client.get("/videos/missing").status_code == 404
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert {"VideoItem", "VideosResponse"} <= set(schemas)


def test_watch_loader_and_api_are_bounded_idempotent_and_source_backed(tmp_path):
    client, Session = _client(tmp_path)
    with Session() as session:
        load_housing(housing_fixture(), session)
        assert load_fixture(_watch_fixture(), session) == {
            "videos": 1, "video_issues": 1, "video_bills": 1,
        }
        assert load_fixture(_watch_fixture(), session) == {
            "videos": 1, "video_issues": 1, "video_bills": 1,
        }
        assert session.query(Video).count() == 1
        assert session.query(VideoIssue).count() == 1
        assert session.query(VideoBill).count() == 1

    response = client.get("/videos").json()
    assert response["total"] == 1
    item = response["videos"][0]
    assert item["video_id"] == "housing-rent-why-rents-move"
    assert item["issue"] == {"slug": "housing-rent", "title": "Housing & Rent"}
    assert [bill["bill_id"] for bill in item["bills"]] == ["hr1-119"]
    assert item["source"]["url"].startswith("https://")
    assert datetime.fromisoformat(item["published_at"])
    assert client.get(f"/videos/{item['video_id']}").json() == item


def test_watch_exposes_only_published_exact_or_issue_discussion(tmp_path):
    client, Session = _client(tmp_path)
    with Session() as session:
        load_housing(housing_fixture(), session)
        load_fixture(_watch_fixture(), session)
        published = DiscussionPost(author_label="Editor", body="Published discussion", moderation_status="published")
        hidden = DiscussionPost(author_label="Editor", body="Hidden discussion", moderation_status="hidden")
        session.add_all((published, hidden)); session.flush()
        session.add(DiscussionAttachment(post_id=published.id, attachment_type="video", video_id="housing-rent-why-rents-move", label="Watch discussion"))
        session.add(DiscussionAttachment(post_id=hidden.id, attachment_type="issue", issue_slug="housing-rent", label="Hidden"))
        session.commit()
        published_id = published.id
    assert client.get("/videos/housing-rent-why-rents-move").json()["discussion_post_id"] == published_id


def test_watch_interactions_are_authenticated_idempotent_private_and_video_scoped(tmp_path):
    client, Session = _client(tmp_path)
    with Session() as session:
        load_housing(housing_fixture(), session)
        load_fixture(_watch_fixture(), session)
        original = session.get(Video, "housing-rent-why-rents-move")
        other = Video(video_id="other-video", creator_label="Editor", caption="Other", media_url=original.media_url, source=original.source, published_at=original.published_at, sort_order=2)
        alice = User(email="alice@example.test", hashed_password="unused")
        bob = User(email="bob@example.test", hashed_password="unused")
        session.add_all((other, alice, bob)); session.flush()
        session.add(VideoIssue(video=other, issue=original.issue_links[0].issue))
        post = DiscussionPost(author_id=alice.id, author_label="Alice", body="Published", moderation_status="published")
        hidden = DiscussionPost(author_id=alice.id, author_label="Alice", body="Hidden", moderation_status="hidden")
        session.add_all((post, hidden)); session.flush()
        session.add_all((
            DiscussionAttachment(post_id=post.id, attachment_type="video", video_id=original.video_id, label="Watch"),
            DiscussionAttachment(post_id=hidden.id, attachment_type="video", video_id=original.video_id, label="Hidden"),
            DiscussionReply(post_id=post.id, author_id=bob.id, body="Published reply", moderation_status="published"),
            VideoSave(user_id=bob.id, video_id=original.video_id),
        ))
        session.commit()
        alice_id = alice.id

    assert client.put("/videos/housing-rent-why-rents-move/like", json={"active": True}).status_code == 401

    def current_user():
        with Session() as session:
            return session.get(User, alice_id)

    client.app.dependency_overrides[get_current_user] = current_user
    client.app.dependency_overrides[get_optional_user] = current_user
    first = client.put("/videos/housing-rent-why-rents-move/like", json={"active": True})
    second = client.put("/videos/housing-rent-why-rents-move/like", json={"active": True})
    saved = client.put("/videos/housing-rent-why-rents-move/save", json={"active": True})
    assert first.status_code == second.status_code == saved.status_code == 200
    assert first.json()["like_count"] == second.json()["like_count"] == 1
    assert saved.json()["saved"] is True

    item = client.get("/videos/housing-rent-why-rents-move").json()
    assert item["liked"] is True and item["saved"] is True
    assert item["discussion_count"] == 2
    assert "save_count" not in item and "savers" not in item
    assert client.get("/videos/other-video").json()["like_count"] == 0
    with Session() as session:
        assert session.query(VideoLike).count() == 1
        assert session.query(VideoSave).count() == 2


def test_watch_cursor_is_deterministic_and_rejects_tampering(tmp_path):
    client, Session = _client(tmp_path)
    with Session() as session:
        load_housing(housing_fixture(), session)
        load_fixture(_watch_fixture(), session)
        original = session.get(Video, "housing-rent-why-rents-move")
        for index in range(1, 4):
            copy = Video(video_id=f"development-video-{index}", creator_label="Development fixture", caption=f"Fixture {index}", transcript="Development-only transcript", media_url=original.media_url, source=original.source, published_at=original.published_at, sort_order=index)
            session.add(copy)
            session.flush()
            session.add(VideoIssue(video=copy, issue=original.issue_links[0].issue))
        session.commit()
    first = client.get("/videos?limit=2").json()
    assert [item["video_id"] for item in first["videos"]] == ["housing-rent-why-rents-move", "development-video-1"]
    assert first["has_more"] is True and first["next_cursor"]
    second = client.get("/videos", params={"limit": 2, "cursor": first["next_cursor"]}).json()
    assert [item["video_id"] for item in second["videos"]] == ["development-video-2", "development-video-3"]
    assert second["has_more"] is False and second["next_cursor"] is None
    assert client.get("/videos", params={"cursor": first["next_cursor"] + "x"}).status_code == 400


def test_watch_loader_rejects_scope_before_writing(tmp_path):
    _, Session = _client(tmp_path)
    payload = deepcopy(_watch_fixture())
    payload["videos"][0]["bill_ids"].append("s968-119")
    with Session() as session:
        with pytest.raises(WatchFixtureValidationError, match="exactly the reviewed"):
            load_fixture(payload, session)
        assert session.query(Video).count() == 0


def test_reviewed_catalog_replacement_is_exact_and_idempotent(tmp_path):
    _, Session = _client(tmp_path)
    reviewed = json.loads((Path(__file__).resolve().parents[1] / "runtime_data" / "watch_census_production_pilot.json").read_text(encoding="utf-8"))
    with Session() as session:
        load_housing(housing_fixture(), session)
        load_fixture(_watch_fixture(), session)
        first = load_fixture(reviewed, session, replace_reviewed_catalog=True)
        second = load_fixture(reviewed, session, replace_reviewed_catalog=True)
        assert first == second == {"videos": 3, "video_issues": 3, "video_bills": 3}
        assert {value for value, in session.query(Video.video_id).all()} == {item["video_id"] for item in reviewed["videos"]}
        assert {value for value, in session.query(VideoBill.bill_id).all()} == {"hr6644-119"}


def test_checked_in_watch_fixture_is_three_item_development_catalog(tmp_path, monkeypatch):
    client, Session = _client(tmp_path)
    payload = json.loads((Path(__file__).resolve().parents[1] / "data" / "watch_housing_rent.json").read_text(encoding="utf-8"))
    assert len(payload["videos"]) == 3
    assert [item["creator_label"] for item in payload["videos"]] == ["Money Instructor", "CNBC", "C-SPAN"]
    assert payload["videos"][0]["delivery"] == {
        "mode": "official_embed",
        "provider": "youtube",
        "provider_video_id": "maODCSHgPww",
        "canonical_url": "https://www.youtube.com/watch?v=maODCSHgPww",
        "source_label": "Money Instructor",
        "development_only": True,
    }
    assert payload["videos"][0]["accessibility"] == {
        "text_kind": "overview",
        "official_transcript_url": "https://www.govinfo.gov/app/details/BILLS-119hr6644enr",
        "official_transcript_label": "Official enrolled H.R. 6644",
        "development_only": True,
    }
    with Session() as session:
        load_housing(housing_fixture(), session)
        assert load_fixture(payload, session) == {"videos": 3, "video_issues": 3, "video_bills": 3}

    disabled = client.get("/videos/housing-rent-road-act-explained").json()
    assert disabled["delivery"] is None and disabled["accessibility"] is None
    monkeypatch.setenv("WTP_ENV", "development")
    monkeypatch.setenv("WTP_ENABLE_DEVELOPMENT_WATCH_EMBED", "true")
    enabled = client.get("/videos/housing-rent-road-act-explained").json()
    assert enabled["delivery"] == payload["videos"][0]["delivery"]
    assert enabled["accessibility"] == payload["videos"][0]["accessibility"]
    assert client.get("/videos/housing-rent-road-act-becomes-law").json()["delivery"]["provider"] == "tiktok"
    assert client.get("/videos/housing-rent-road-act-speaker").json()["delivery"]["provider"] == "facebook"

    monkeypatch.setenv("WTP_ENV", "production")
    monkeypatch.delenv("WTP_ENABLE_DEVELOPMENT_WATCH_EMBED")
    production_disabled = client.get("/videos/housing-rent-road-act-explained").json()
    assert production_disabled["delivery"]["mode"] == "link_out"
    assert production_disabled["accessibility"]["official_transcript_label"] == "Official enrolled H.R. 6644"
    monkeypatch.setenv("WTP_ENABLE_PRODUCTION_WATCH_EMBED", "true")
    production_enabled = client.get("/videos/housing-rent-road-act-explained").json()
    assert production_enabled["delivery"] == payload["videos"][0]["delivery"] | {"development_only": False}
    assert production_enabled["accessibility"] == payload["videos"][0]["accessibility"] | {"development_only": False}
    assert client.get("/videos/housing-rent-road-act-becomes-law").json()["delivery"]["provider"] == "tiktok"
    assert client.get("/videos/housing-rent-road-act-speaker").json()["delivery"]["provider"] == "facebook"


def test_watch_loader_rejects_unsafe_official_embed_metadata():
    payload = _watch_fixture()
    payload["videos"][0]["delivery"] = {
        "mode": "official_embed",
        "provider": "youtube",
        "provider_video_id": "example",
        "canonical_url": "https://www.youtube.com/watch?v=example",
        "source_label": "Official source",
        "development_only": False,
    }
    with pytest.raises(WatchFixtureValidationError, match="must remain development_only"):
        validate_fixture(payload)


def test_watch_loader_rejects_unsafe_accessibility_metadata():
    payload = _watch_fixture()
    payload["videos"][0]["accessibility"] = {
        "text_kind": "overview",
        "official_transcript_url": "http://example.test/transcript.pdf",
        "official_transcript_label": "Official transcript",
        "development_only": True,
    }
    with pytest.raises(WatchFixtureValidationError, match="must use HTTPS"):
        validate_fixture(payload)


def test_watch_share_preview_is_canonical_source_backed_and_missing_safe(tmp_path):
    client, Session = _client(tmp_path)
    with Session() as session:
        load_housing(housing_fixture(), session)
        load_fixture(_watch_fixture(), session)

    preview = client.get("/videos/housing-rent-why-rents-move/share")
    assert preview.status_code == 200
    assert preview.json() == {
        "video_id": "housing-rent-why-rents-move",
        "canonical_url": "https://app.wethepeople.place/watch/housing-rent-why-rents-move",
        "title": "Start with official housing evidence. | WeThePeople.place",
        "description": "WeThePeople.place · Housing & Rent · Source: Congress.gov",
        "image_url": "https://app.wethepeople.place/og-image.png",
        "source": {
            "url": "https://www.congress.gov/bill/119th-congress/house-bill/1",
            "publisher": "Congress.gov",
            "retrieved_at": "2026-07-31T00:00:00",
        },
    }
    assert client.get("/videos/missing/share").status_code == 404
    html = client.get("/videos/housing-rent-why-rents-move/preview")
    assert html.status_code == 200
    assert '<link rel="canonical" href="https://app.wethepeople.place/watch/housing-rent-why-rents-move">' in html.text
    assert '<meta property="og:title" content="Start with official housing evidence. | WeThePeople.place">' in html.text
    assert "Congress.gov" in html.text
    assert client.get("/videos/missing/preview").status_code == 404
