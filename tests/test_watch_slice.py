from copy import deepcopy
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from jobs.load_housing_rent_slice import load_fixture as load_housing
from jobs.load_watch_fixture import WatchFixtureValidationError, load_fixture
from models.database import Base, get_db
from models.issue_models import Video, VideoBill, VideoIssue
from routers.videos import router
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
    assert client.get("/videos").json() == {"total": 0, "videos": []}
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


def test_watch_loader_rejects_scope_before_writing(tmp_path):
    _, Session = _client(tmp_path)
    payload = deepcopy(_watch_fixture())
    payload["videos"][0]["bill_ids"].append("s968-119")
    with Session() as session:
        with pytest.raises(WatchFixtureValidationError, match="exactly the reviewed"):
            load_fixture(payload, session)
        assert session.query(Video).count() == 0


def test_watch_share_preview_is_canonical_source_backed_and_missing_safe(tmp_path):
    client, Session = _client(tmp_path)
    with Session() as session:
        load_housing(housing_fixture(), session)
        load_fixture(_watch_fixture(), session)

    preview = client.get("/videos/housing-rent-why-rents-move/share")
    assert preview.status_code == 200
    assert preview.json() == {
        "video_id": "housing-rent-why-rents-move",
        "canonical_url": "https://wethepeople.place/watch/housing-rent-why-rents-move",
        "title": "Start with official housing evidence. | WeThePeople.place",
        "description": "WeThePeople.place · Housing & Rent · Source: Congress.gov",
        "image_url": "https://wethepeople.place/og-image.png",
        "source": {
            "url": "https://www.congress.gov/bill/119th-congress/house-bill/1",
            "publisher": "Congress.gov",
            "retrieved_at": "2026-07-31T00:00:00",
        },
    }
    assert client.get("/videos/missing/share").status_code == 404
    html = client.get("/videos/housing-rent-why-rents-move/preview")
    assert html.status_code == 200
    assert '<link rel="canonical" href="https://wethepeople.place/watch/housing-rent-why-rents-move">' in html.text
    assert '<meta property="og:title" content="Start with official housing evidence. | WeThePeople.place">' in html.text
    assert "Congress.gov" in html.text
    assert client.get("/videos/missing/preview").status_code == 404
