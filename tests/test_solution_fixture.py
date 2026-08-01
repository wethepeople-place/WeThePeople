from copy import deepcopy

import pytest

from jobs.load_discuss_fixture import load_fixture as load_discuss
from jobs.load_housing_rent_slice import load_fixture as load_housing
from jobs.load_solution_fixture import SolutionFixtureValidationError, load_fixture
from jobs.load_watch_fixture import load_fixture as load_watch
from models.auth_models import User
from models.civic_models import Proposal, SolutionRevision
from models.social_models import DiscussionAttachment
from tests.test_discussions_api import _discuss_fixture, _environment
from tests.test_housing_rent_loader import _fixture as housing_fixture
from tests.test_watch_slice import _watch_fixture


def _fixture():
    return {"solutions": [{
        "issue_slug": "housing-rent",
        "title": "Pilot faster rental assistance delivery",
        "summary": "Test a time-limited process for reducing verified rental-assistance processing delays while preserving eligibility review and public reporting.",
        "body": "Congress should authorize a bounded demonstration in participating jurisdictions that publishes eligibility rules, processing-time measures, administrative costs, and independent evaluation results. The pilot should sunset unless lawmakers review the evidence and renew it.",
        "change_note": "Initial reviewed Housing & Rent solution",
        "discussion_body": "What should Congress prioritize first to make rent more affordable? Start with the evidence, then explain the tradeoff behind your answer.",
    }]}


def test_solution_fixture_is_bounded_idempotent_and_discussion_linked():
    _, _, Session = _environment()
    with Session() as session:
        load_housing(housing_fixture(), session)
        load_watch(_watch_fixture(), session)
        load_discuss(_discuss_fixture(), session)
        user = User(email="editor@example.test", hashed_password="test", display_name="Editor")
        session.add(user)
        session.commit()
        first = load_fixture(_fixture(), session, user.id)
        second = load_fixture(_fixture(), session, user.id)
        assert first == second == {"solutions": 1, "revisions": 1, "discussion_attachments": 1}
        solution = session.query(Proposal).one()
        assert solution.issue_slug == "housing-rent" and solution.author_id == user.id
        assert session.query(SolutionRevision).count() == 1
        link = session.query(DiscussionAttachment).filter_by(attachment_type="solution").one()
        assert link.solution_id == solution.id


def test_solution_fixture_rejects_scope_before_writing():
    _, _, Session = _environment()
    payload = deepcopy(_fixture())
    payload["solutions"][0]["issue_slug"] = "transportation"
    with Session() as session:
        with pytest.raises(SolutionFixtureValidationError):
            load_fixture(payload, session, 999)
        assert session.query(Proposal).count() == 0
