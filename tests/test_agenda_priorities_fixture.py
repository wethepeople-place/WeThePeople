import json
from copy import deepcopy

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from jobs.load_agenda_priorities import (
    AGENDA_FIXTURE_PATH,
    AgendaFixtureValidationError,
    load_fixture,
    validate_fixture,
)
from models.database import Base, SourceDocument
from models.issue_models import Issue


def _payload():
    return json.loads(AGENDA_FIXTURE_PATH.read_text(encoding="utf-8"))


def test_reviewed_agenda_fixture_is_exactly_20_ranked_sourced_issues():
    payload = _payload()
    validate_fixture(payload)
    assert [item["rank"] for item in payload["items"]] == list(range(1, 21))
    assert payload["items"][0] == {
        "rank": 1,
        "slug": "immigration",
        "title": "Immigration",
        "priority_share": 44,
        "summary": "Immigration, border policy, DACA, family separation, and ICE.",
    }
    assert payload["items"][5]["slug"] == "housing-rent"
    assert payload["methodology"]["sample_size"] == 1146


def test_agenda_loader_is_idempotent_and_preserves_existing_housing_summary():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        session.add(Issue(slug="housing-rent", title="Housing & Rent", summary="Reviewed housing receipts."))
        session.commit()
        first = load_fixture(_payload(), session)
        second = load_fixture(_payload(), session)
        assert first == {"agenda_issues": 20, "created": 19, "sources": 1}
        assert second == {"agenda_issues": 20, "created": 0, "sources": 1}
        assert session.get(Issue, "housing-rent").summary == "Reviewed housing receipts."
        assert session.query(SourceDocument).count() == 1


def test_agenda_fixture_rejects_rank_and_source_drift():
    payload = deepcopy(_payload())
    payload["items"][1]["rank"] = 1
    with pytest.raises(AgendaFixtureValidationError):
        validate_fixture(payload)

    payload = deepcopy(_payload())
    payload["methodology"]["topline_url"] = "http://example.com/topline.pdf"
    with pytest.raises(AgendaFixtureValidationError):
        validate_fixture(payload)
