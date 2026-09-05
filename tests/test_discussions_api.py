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
from models.social_models import (
    DiscussionAttachment,
    DiscussionBookmark,
    DiscussionBlock,
    DiscussionPost,
    DiscussionReaction,
    DiscussionReport,
    DiscussionVideoLink,
)
from models.issue_models import Issue
from routers.discussions import router
from services.jwt_auth import get_current_user, get_optional_user
from services.social_link_classifier import rank_agenda_issues
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


def test_community_feed_filters_structured_proposals_and_videos_without_duplicate_stores():
    _, client, Session = _environment()
    _seed(Session)
    with Session() as session:
        proposal = DiscussionPost(author_label="Alice", body="Build more homes near transit", moderation_status="published")
        proposal.attachments.extend([
            DiscussionAttachment(attachment_type="issue", issue_slug="housing-rent", label="Housing & Rent"),
            DiscussionAttachment(attachment_type="solution", solution_id=42, label="Build near transit"),
        ])
        session.add(proposal)
        session.commit()
    proposals = client.get("/discussions", params={"issue_slug": "housing-rent", "content": "proposals"}).json()
    videos = client.get("/discussions", params={"issue_slug": "housing-rent", "content": "videos"}).json()
    discussions = client.get("/discussions", params={"issue_slug": "housing-rent", "content": "discussions"}).json()
    assert proposals["total"] == 1 and proposals["items"][0]["body"] == "Build more homes near transit"
    assert videos["total"] == 0
    assert discussions["total"] == 0
    assert all(not any(attachment["type"] in {"solution", "video"} for attachment in item["attachments"]) for item in discussions["items"])


def test_discuss_continuation_reuses_reviewed_records_without_duplicating_community_posts():
    _, client, Session = _environment()
    _seed(Session)
    response = client.get("/discussions/continuation")
    assert response.status_code == 200
    payload = response.json()
    assert payload["reviewed_videos"]
    assert all(item["content_origin"] == "reviewed" for item in payload["reviewed_videos"])
    assert len({item["video_id"] for item in payload["reviewed_videos"]}) == len(payload["reviewed_videos"])
    assert payload["agenda"][0]["slug"] == "housing-rent"
    assert payload["bills"] and payload["bills"][0]["bill_id"]


def test_video_comments_endpoint_uses_the_shared_published_conversation():
    _, client, Session = _environment()
    _seed(Session)

    response = client.get("/discussions/videos/housing-rent-why-rents-move")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["body"].startswith("What should Congress prioritize")
    assert client.get("/discussions/videos/not-a-video").status_code == 404


def test_video_comment_requires_auth_and_is_attached_for_moderation():
    app, client, Session = _environment()
    alice_id, _ = _seed(Session)
    endpoint = "/discussions/videos/housing-rent-why-rents-move/comments"

    assert client.post(endpoint, json={"body": "Housing evidence matters."}).status_code == 401
    _as_user(app, Session, alice_id)
    created = client.post(endpoint, json={"body": "  Housing evidence matters.  "})
    assert created.status_code == 201
    assert created.json()["moderation_status"] == "pending"

    with Session() as session:
        post = session.get(DiscussionPost, created.json()["id"])
        assert post.body == "Housing evidence matters."
        assert post.moderation_status == "pending"
        attachments = session.query(DiscussionAttachment).filter_by(post_id=post.id).all()
        assert {
            (item.attachment_type, item.video_id or item.issue_slug)
            for item in attachments
        } == {
            ("issue", "housing-rent"),
            ("video", "housing-rent-why-rents-move"),
        }

    assert client.get("/discussions/videos/housing-rent-why-rents-move").json()["total"] == 1
    assert client.post("/discussions/videos/not-a-video/comments", json={"body": "No target"}).status_code == 404


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


def test_post_reactions_are_public_and_bookmarks_remain_private_and_idempotent():
    app, client, Session = _environment()
    alice_id, bob_id = _seed(Session)
    post_id = client.get("/discussions").json()["items"][0]["id"]

    assert client.put(f"/discussions/{post_id}/reactions/like").status_code == 401
    assert client.put(f"/discussions/{post_id}/bookmark").status_code == 401
    _as_user(app, Session, alice_id)
    first = client.put(f"/discussions/{post_id}/reactions/like")
    second = client.put(f"/discussions/{post_id}/reactions/like")
    assert first.json()["reactions"]["like"] == second.json()["reactions"]["like"] == 1
    assert client.put(f"/discussions/{post_id}/bookmark").json() == {"bookmarked": True}
    assert client.put(f"/discussions/{post_id}/bookmark").json() == {"bookmarked": True}

    viewer_feed = client.get("/discussions").json()["items"][0]
    assert viewer_feed["viewer_reactions"] == ["like"]
    assert viewer_feed["viewer_bookmarked"] is True
    assert viewer_feed["reactions"] == {"like": 1, "insightful": 0, "disagree": 0}

    _as_user(app, Session, bob_id)
    public_feed = client.get("/discussions").json()["items"][0]
    assert public_feed["reactions"]["like"] == 1
    assert public_feed["viewer_reactions"] == []
    assert public_feed["viewer_bookmarked"] is False

    _as_user(app, Session, alice_id)
    assert client.delete(f"/discussions/{post_id}/reactions/like").json()["reactions"]["like"] == 0
    assert client.delete(f"/discussions/{post_id}/bookmark").json() == {"bookmarked": False}
    with Session() as session:
        assert session.query(DiscussionReaction).count() == 0
        assert session.query(DiscussionBookmark).count() == 0


def test_social_post_is_normalized_connected_to_an_agenda_and_published_immediately():
    app, client, Session = _environment()
    alice_id, _ = _seed(Session)
    assert client.post("/discussions", json={"body": "Worth discussing", "video_url": "https://youtu.be/maODCSHgPww"}).status_code == 401

    _as_user(app, Session, alice_id)
    created = client.post("/discussions", json={
        "body": "  What policy tradeoff does this highlight?  ",
        "video_url": "https://www.youtube.com/watch?v=maODCSHgPww&utm_source=test",
        "issue_slug": "housing-rent",
    })
    assert created.status_code == 201
    assert created.json()["moderation_status"] == "published"
    with Session() as session:
        post = session.get(DiscussionPost, created.json()["id"])
        assert post.body == "What policy tradeoff does this highlight?"
        assert post.moderation_status == "published"
        assert post.video_link.canonical_url == "https://www.youtube.com/watch?v=maODCSHgPww"

    public = client.get(f"/discussions/{created.json()['id']}")
    assert public.status_code == 200
    assert public.json()["video_link"] == {
        "provider": "youtube",
        "provider_video_id": "maODCSHgPww",
        "canonical_url": "https://www.youtube.com/watch?v=maODCSHgPww",
    }

    cases = (
        ("https://www.tiktok.com/@civic.creator/video/7512345678901234567?lang=en", "tiktok", "7512345678901234567", "https://www.tiktok.com/@civic.creator/video/7512345678901234567"),
        ("https://www.facebook.com/civic.page/videos/123456789012345/?tracking=1", "facebook", "123456789012345", "https://www.facebook.com/civic.page/videos/123456789012345"),
        ("https://www.instagram.com/reel/ABC_def-123/?utm_source=share", "instagram", "ABC_def-123", "https://www.instagram.com/reel/ABC_def-123/"),
    )
    for url, provider, provider_id, canonical_url in cases:
        response = client.post("/discussions", json={
            "body": f"Review this {provider} source",
            "video_url": url,
            "issue_slug": "housing-rent",
        })
        assert response.status_code == 201
        assert response.json()["moderation_status"] == "published"
        with Session() as session:
            link = session.get(DiscussionPost, response.json()["id"]).video_link
            assert (link.provider, link.provider_video_id, link.canonical_url) == (provider, provider_id, canonical_url)


def test_text_only_post_is_allowed_and_published_for_an_authenticated_user():
    app, client, Session = _environment()
    alice_id, _ = _seed(Session)
    _as_user(app, Session, alice_id)
    created = client.post("/discussions", json={"body": "  What evidence should we examine next?  "})
    assert created.status_code == 201
    assert created.json()["moderation_status"] == "published"
    with Session() as session:
        post = session.get(DiscussionPost, created.json()["id"])
        assert post.body == "What evidence should we examine next?"
        assert post.moderation_status == "published"
        assert post.video_link is None


def test_youtube_short_is_normalized_and_classified_without_user_help(monkeypatch):
    app, client, Session = _environment()
    alice_id, _ = _seed(Session)
    with Session() as session:
        session.add(Issue(slug="crime-violence", title="Crime & Violence"))
        session.commit()
    _as_user(app, Session, alice_id)
    monkeypatch.setattr(
        "routers.discussions.fetch_social_metadata",
        lambda provider, url: "Hemp growers and sellers take Texas to court over THC ban WFAA",
    )

    created = client.post(
        "/discussions",
        json={"video_url": "https://www.youtube.com/shorts/ssTeslcxXbY"},
    )

    assert created.status_code == 201
    assert created.json()["moderation_status"] == "published"
    detail = client.get(f"/discussions/{created.json()['id']}").json()
    assert detail["video_link"] == {
        "provider": "youtube",
        "provider_video_id": "ssTeslcxXbY",
        "canonical_url": "https://www.youtube.com/watch?v=ssTeslcxXbY",
    }
    assert detail["attachments"][0]["reference_id"] == "crime-violence"
    assert detail["attachments"][0]["label"] == "Crime & Violence"


def test_youtube_homelessness_video_is_classified_without_user_help(monkeypatch):
    app, client, Session = _environment()
    alice_id, _ = _seed(Session)
    with Session() as session:
        session.add(Issue(slug="poverty-hunger-homelessness", title="Poverty, Hunger & Homelessness"))
        session.commit()
    _as_user(app, Session, alice_id)
    monkeypatch.setattr(
        "routers.discussions.fetch_social_metadata",
        lambda provider, url: "What's behind rising homelessness in America? YouTube",
    )

    created = client.post(
        "/discussions",
        json={"video_url": "https://www.youtube.com/watch?v=KUpIEDqbVyk"},
    )

    assert created.status_code == 201
    detail = client.get(f"/discussions/{created.json()['id']}").json()
    assert detail["video_link"]["provider_video_id"] == "KUpIEDqbVyk"
    assert detail["attachments"][0]["reference_id"] == "poverty-hunger-homelessness"
    assert detail["attachments"][0]["label"] == "Poverty, Hunger & Homelessness"


def test_classifier_matches_related_word_forms_across_the_reviewed_vocabulary():
    cases = (
        ("homelessness is rising", "poverty-hunger-homelessness"),
        ("immigrants at the border", "immigration"),
        ("grocery prices increased", "food-costs-security"),
        ("tariffs affect imports", "trade-tariffs"),
        ("medical bills and insurance premiums", "health-care-costs"),
        ("shootings threaten public safety", "crime-violence"),
    )
    slugs = (
        "poverty-hunger-homelessness",
        "immigration",
        "food-costs-security",
        "trade-tariffs",
        "health-care-costs",
        "crime-violence",
    )
    for text, expected in cases:
        assert rank_agenda_issues(text, slugs)[0].slug == expected


def test_classifier_selects_each_reviewed_agenda_issue_from_realistic_metadata():
    cases = {
        "immigration": "Immigrants face deportation at the border as asylum rules change",
        "economy": "Economic recession concerns weigh on consumer confidence and GDP",
        "health-care-reform": "Universal healthcare and health insurance coverage reform",
        "cost-of-living": "Household budgets squeezed by living expenses and affordability",
        "inflation": "Inflation erodes purchasing power as prices rise",
        "housing-rent": "Renters face evictions while mortgages and home prices increase",
        "education-student-debt": "Schools teachers tuition and student loans shape education policy",
        "jobs-unemployment": "Layoffs hiring and unemployment reshape the job market",
        "poverty-hunger-homelessness": "Homelessness hunger poverty and shelters strain communities",
        "taxes": "Income taxes corporate tax rates and tax reform",
        "climate-environment": "Climate pollution emissions and global warming threaten the environment",
        "crime-violence": "Shootings violence and hate crimes raise public safety concerns",
        "health-care-costs": "Medical bills insurance premiums prescription costs and deductibles",
        "food-costs-security": "Groceries and food prices drive food insecurity",
        "federal-budget-debt": "Federal deficits national debt government spending and the debt ceiling",
        "welfare-entitlements": "Welfare public benefits eligibility and entitlement reforms",
        "wages": "Minimum wages worker pay and wage growth",
        "government-corruption": "Government fraud bribery ethics violations and accountability",
        "social-security": "Social Security retirement benefits and program financing",
        "trade-tariffs": "Tariffs imports exports and trade agreements",
    }
    slugs = tuple(cases)

    for expected, text in cases.items():
        matches = rank_agenda_issues(text, slugs)
        assert matches, expected
        assert matches[0].slug == expected, (expected, matches)


def test_video_post_rejects_untrusted_or_malformed_links():
    for url in (
        "http://www.youtube.com/watch?v=maODCSHgPww",
        "https://evil.example/watch?v=maODCSHgPww",
        "https://www.youtube.com/watch?v=not-valid",
        "https://www.youtube.com.evil.example/watch?v=maODCSHgPww",
        "https://www.tiktok.com.evil.example/@person/video/7512345678901234567",
        "https://www.instagram.com/profile-name/",
        "https://fb.watch/unresolved-short-link/",
    ):
        app, client, Session = _environment()
        alice_id, _ = _seed(Session)
        _as_user(app, Session, alice_id)
        assert client.post("/discussions", json={"body": "Discuss", "video_url": url}).status_code == 422
        with Session() as session:
            assert session.query(DiscussionVideoLink).count() == 0


def test_social_link_asks_for_topic_only_when_automatic_matching_fails(monkeypatch):
    app, client, Session = _environment()
    alice_id, _ = _seed(Session)
    _as_user(app, Session, alice_id)
    monkeypatch.setattr("routers.discussions.fetch_social_metadata", lambda provider, url: "")
    missing = client.post("/discussions", json={
        "body": "Where does this belong?",
        "video_url": "https://www.instagram.com/p/ABC_def-123/",
    })
    assert missing.status_code == 422
    assert missing.json()["detail"] == "We could not match this link yet. Add a few words about its topic and try again"
    unknown = client.post("/discussions", json={
        "body": "Unknown issue",
        "video_url": "https://www.instagram.com/p/ABC_def-123/",
        "issue_slug": "not-reviewed",
    })
    assert unknown.status_code == 422
    assert unknown.json()["detail"] == "Choose a reviewed WTP issue"


def test_link_suggestion_uses_provider_metadata_and_returns_ranked_reviewed_issue(monkeypatch):
    app, client, Session = _environment()
    alice_id, _ = _seed(Session)
    with Session() as session:
        session.add_all((
            Issue(slug="health-care-reform", title="Health Care Reform"),
            Issue(slug="health-care-costs", title="Health Care Costs"),
        ))
        session.commit()
    _as_user(app, Session, alice_id)
    monkeypatch.setattr(
        "routers.discussions.fetch_social_metadata",
        lambda provider, url: "Our system is so broken #healthinsurance #universalhealthcare #chronicillness",
    )
    response = client.post("/discussions/link-suggestion", json={
        "video_url": "https://www.tiktok.com/@lemonsnlyme/video/7679228789091519757?sender_device=pc",
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["canonical_url"] == "https://www.tiktok.com/@lemonsnlyme/video/7679228789091519757"
    assert payload["suggested_issue"]["slug"] == "health-care-reform"
    assert payload["confidence"] == "high"


def test_link_post_allows_an_empty_take_and_uses_a_neutral_system_body():
    app, client, Session = _environment()
    alice_id, _ = _seed(Session)
    _as_user(app, Session, alice_id)
    response = client.post("/discussions", json={
        "body": "",
        "video_url": "https://www.tiktok.com/@lemonsnlyme/video/7679228789091519757",
        "issue_slug": "housing-rent",
    })
    assert response.status_code == 201
    with Session() as session:
        post = session.get(DiscussionPost, response.json()["id"])
        assert post.body == "Shared a Tiktok video."
        assert post.moderation_status == "published"


def test_link_post_automatically_attaches_the_best_issue_without_user_selection(monkeypatch):
    app, client, Session = _environment()
    alice_id, _ = _seed(Session)
    with Session() as session:
        session.add(Issue(slug="health-care-reform", title="Health Care Reform"))
        session.commit()
    _as_user(app, Session, alice_id)
    monkeypatch.setattr(
        "routers.discussions.fetch_social_metadata",
        lambda provider, url: "#healthinsurance #universalhealthcare",
    )
    response = client.post("/discussions", json={
        "video_url": "https://www.tiktok.com/@lemonsnlyme/video/7679228789091519757",
    })
    assert response.status_code == 201
    assert response.json()["moderation_status"] == "published"
    with Session() as session:
        post = session.get(DiscussionPost, response.json()["id"])
        assert [(item.attachment_type, item.issue_slug) for item in post.attachments] == [
            ("issue", "health-care-reform")
        ]
        assert post.attachments[0].label == "Health Care Reform"
