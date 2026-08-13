import pytest

from jobs.housing_rent_contract import (
    CURATED_BILLS,
    EVIDENCE_SERIES,
    ISSUE_SLUG,
    VALIDATION_ZIP,
    classify_phase,
)


def test_slice_scope_is_exact_and_uses_canonical_identifiers():
    assert ISSUE_SLUG == "housing-rent"
    assert VALIDATION_ZIP == "49001"
    assert {series.key for series in EVIDENCE_SERIES} == {"hud_fmr_2br_proxy", "rent_cpi", "avg_wage"}

    expected_bill_ids = {
        "hr1-119",
        "hr6644-119",
        "s968-119",
        "hr6124-119",
        "s3207-119",
        "hr2725-119",
        "s1515-119",
    }
    assert {bill.bill_id for bill in CURATED_BILLS} == expected_bill_ids
    assert len(CURATED_BILLS) == len(expected_bill_ids) == 7
    assert all(
        bill.bill_id == f"{bill.bill_type}{bill.bill_number}-{bill.congress}"
        for bill in CURATED_BILLS
    )


def test_evidence_series_sources_are_named_and_https():
    for series in EVIDENCE_SERIES:
        assert series.publisher
        assert series.source_url.startswith("https://")


@pytest.mark.parametrize(
    ("bucket", "actions", "expected"),
    [
        ("enacted", [], "past"),
        ("failed", [], "past"),
        ("passed_house", [], "current"),
        ("in_committee", ["Committee hearing held"], "current"),
        ("in_committee", ["Referred to the Committee on Finance"], "upcoming"),
        ("introduced", [], "upcoming"),
    ],
)
def test_status_mapping_preserves_reviewed_meanings(bucket, actions, expected):
    assert classify_phase(bucket, actions) == expected


def test_unknown_status_fails_closed_for_human_review():
    with pytest.raises(ValueError, match="Unreviewed bill status bucket"):
        classify_phase("mystery_status")
