"""Immutable contract for the first Housing & Rent civic-data slice.

This module deliberately performs no network or database work. It centralizes
the reviewed scope and classification rules that later ingestion must obey.
"""

from dataclasses import dataclass
from typing import Literal, Sequence


ISSUE_SLUG = "housing-rent"
VALIDATION_ZIP = "49001"
Phase = Literal["past", "current", "upcoming"]


@dataclass(frozen=True)
class EvidenceSeriesSpec:
    key: str
    publisher: str
    source_url: str


@dataclass(frozen=True)
class CuratedBillSpec:
    bill_id: str
    congress: int
    bill_type: str
    bill_number: int


EVIDENCE_SERIES = (
    EvidenceSeriesSpec(
        key="rent_cpi",
        publisher="U.S. Bureau of Labor Statistics",
        source_url="https://www.bls.gov/cpi/factsheets/owners-equivalent-rent-and-rent.htm",
    ),
    EvidenceSeriesSpec(
        key="avg_wage",
        publisher="U.S. Bureau of Labor Statistics",
        source_url="https://www.bls.gov/developers/",
    ),
)


CURATED_BILLS = (
    CuratedBillSpec("hr1-119", 119, "hr", 1),
    CuratedBillSpec("hr6644-119", 119, "hr", 6644),
    CuratedBillSpec("s968-119", 119, "s", 968),
    CuratedBillSpec("hr6124-119", 119, "hr", 6124),
    CuratedBillSpec("s3207-119", 119, "s", 3207),
    CuratedBillSpec("hr2725-119", 119, "hr", 2725),
    CuratedBillSpec("s1515-119", 119, "s", 1515),
)


_PAST_BUCKETS = {"enacted", "became_law", "signed", "failed", "vetoed"}
_CURRENT_BUCKETS = {"passed_one", "passed_house", "passed_senate", "passed_both"}
_UPCOMING_BUCKETS = {"introduced", "in_committee"}
_SUBSTANTIVE_COMMITTEE_MARKERS = (
    "hearing",
    "markup",
    "ordered to be reported",
    "reported by",
    "reported to",
)


def classify_phase(status_bucket: str, action_texts: Sequence[str] = ()) -> Phase:
    """Map upstream lifecycle data to the reviewed three-phase UI contract.

    A routine referral is intentionally not substantive committee work. Values
    outside the reviewed mapping raise instead of receiving a guessed phase.
    """

    bucket = status_bucket.strip().lower()
    actions = "\n".join(action_texts).lower()

    if bucket in _PAST_BUCKETS:
        return "past"
    if bucket in _CURRENT_BUCKETS:
        return "current"
    if any(marker in actions for marker in _SUBSTANTIVE_COMMITTEE_MARKERS):
        return "current"
    if bucket in _UPCOMING_BUCKETS:
        return "upcoming"
    raise ValueError(f"Unreviewed bill status bucket: {status_bucket!r}")
