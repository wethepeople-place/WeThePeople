import json
from copy import deepcopy
from pathlib import Path

import pytest

from jobs.load_discussion_demo import (
    DiscussionDemoError,
    assert_local_demo_environment,
    assert_production_demo_environment,
    clear_fixture,
    load_fixture,
)
from jobs.load_housing_rent_slice import load_fixture as load_housing
from jobs.load_watch_fixture import load_fixture as load_watch
from models.auth_models import User
from models.social_models import DiscussionPost, DiscussionReaction, DiscussionReply
from tests.test_discussions_api import _environment
from tests.test_housing_rent_loader import _fixture as housing_fixture

FIXTURE = Path(__file__).parents[1] / "data" / "discussion_demo_synthetic.json"
WATCH_FIXTURE = Path(__file__).parents[1] / "runtime_data" / "watch_census_production_pilot.json"


def test_environment_gate_rejects_non_synthetic_or_non_demo_databases():
    with pytest.raises(DiscussionDemoError):
        assert_local_demo_environment({}, "sqlite:///./discussion-demo.db")
    with pytest.raises(DiscussionDemoError):
        assert_local_demo_environment(
            {"WTP_DATA_CLASSIFICATION": "synthetic", "WTP_TARGET_ENV": "production"},
            "sqlite:///./discussion-demo.db",
        )
    with pytest.raises(DiscussionDemoError):
        assert_local_demo_environment(
            {"WTP_DATA_CLASSIFICATION": "synthetic", "WTP_TARGET_ENV": "local"},
            "sqlite:///./wethepeople.db",
        )
    assert_local_demo_environment(
        {"WTP_DATA_CLASSIFICATION": "synthetic", "WTP_TARGET_ENV": "local"},
        "sqlite:///./discussion-demo.db",
    )


def test_production_gate_requires_exact_dataset_and_confirmation():
    approved = {
        "WTP_DATA_CLASSIFICATION": "synthetic",
        "WTP_TARGET_ENV": "production",
        "WTP_ALLOW_PUBLIC_SYNTHETIC_DEMO": "wtp-discussion-demo-v2-latin",
    }
    with pytest.raises(DiscussionDemoError):
        assert_production_demo_environment("", approved, "sqlite:////opt/wethepeople/data/wethepeople.db")
    with pytest.raises(DiscussionDemoError):
        assert_production_demo_environment(
            "publish-bounded-latin-demo",
            {**approved, "WTP_ALLOW_PUBLIC_SYNTHETIC_DEMO": "wrong-dataset"},
            "sqlite:////opt/wethepeople/data/wethepeople.db",
        )
    assert_production_demo_environment(
        "publish-bounded-latin-demo", approved, "sqlite:////opt/wethepeople/data/wethepeople.db"
    )


def test_demo_fixture_is_bounded_idempotent_and_removable():
    _, client, Session = _environment()
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    with Session() as session:
        load_housing(housing_fixture(), session)
        load_watch(json.loads(WATCH_FIXTURE.read_text(encoding="utf-8")), session, replace_reviewed_catalog=True)
        first = load_fixture(payload, session, classification="synthetic")
        second = load_fixture(payload, session, classification="synthetic")
        assert first == second == {"users": 6, "posts": 8, "replies": 12, "reactions": 20}
        assert session.query(User).filter(User.email.like("demo.discussion.%")).count() == 6
        assert session.query(DiscussionPost).count() == 8
        assert session.query(DiscussionReply).count() == 12
        assert session.query(DiscussionReaction).count() == 20
    feed = client.get("/discussions").json()
    assert feed["total"] == 8
    assert all(item["author"]["display_name"].endswith("(Demo)") for item in feed["items"])
    assert all(item["author"]["is_demo"] is True for item in feed["items"])
    assert all(item["body"].endswith("[Demo discussion]") for item in feed["items"])
    assert client.get("/discussions/videos/housing-rent-road-act-explained").json()["total"] == 2
    with Session() as session:
        assert clear_fixture(session, classification="synthetic") == {"users_removed": 6, "posts_removed": 8}
        assert session.query(DiscussionPost).count() == 0


def test_demo_fixture_rejects_unmarked_copy_before_writing():
    _, _, Session = _environment()
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    hostile = deepcopy(payload)
    hostile["posts"][0]["body"] = "Looks real"
    with Session() as session:
        with pytest.raises(DiscussionDemoError):
            load_fixture(hostile, session, classification="synthetic")
        assert session.query(DiscussionPost).count() == 0


def test_demo_fixture_uses_obvious_latin_placeholders_and_numbered_users():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert payload["dataset"] == "wtp-discussion-demo-v2-latin"
    assert [user["display_name"] for user in payload["users"]] == [
        f"Test User {index:02d} (Demo)" for index in range(1, 7)
    ]
    assert all("[Demo discussion]" in post["body"] for post in payload["posts"])
    assert all(
        any(word in post["body"].lower() for word in ("lorem", "praesent", "maecenas", "fusce", "cras", "vestibulum", "nullam", "donec"))
        for post in payload["posts"]
    )
