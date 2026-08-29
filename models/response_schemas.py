"""
Pydantic response models for the WeThePeople API.

These models document the exact shape of API responses and are used as
``response_model`` on endpoint decorators so that OpenAPI/Swagger docs
expose accurate schemas.  They intentionally mirror the dicts already
returned by each endpoint -- no behaviour changes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. GET /health
# ---------------------------------------------------------------------------

class DatabaseStatus(BaseModel):
    connected: bool

class HealthResponse(BaseModel):
    status: str
    database: DatabaseStatus


# ---------------------------------------------------------------------------
# 2. GET /politics/dashboard/stats (alias: /dashboard/stats on politics router)
# ---------------------------------------------------------------------------

class PoliticsDashboardStats(BaseModel):
    total_people: int
    total_claims: int
    total_actions: int
    total_bills: int
    by_tier: Dict[str, int]
    match_rate: float


# ---------------------------------------------------------------------------
# 3. GET /people  (politics people directory)
# ---------------------------------------------------------------------------

class PersonListItem(BaseModel):
    person_id: str
    display_name: Optional[str] = None
    chamber: Optional[str] = None
    state: Optional[str] = None
    party: Optional[str] = None
    is_active: bool
    photo_url: Optional[str] = None
    ai_profile_summary: Optional[str] = None
    sanctions_status: Optional[str] = None

class PeopleListResponse(BaseModel):
    total: int
    people: List[PersonListItem]
    limit: int
    offset: int
    dataset_updated_at: Optional[str] = None


# ---------------------------------------------------------------------------
# 4. GET /people/{person_id}
# ---------------------------------------------------------------------------

class PersonDetailResponse(BaseModel):
    person_id: str
    display_name: Optional[str] = None
    bioguide_id: Optional[str] = None
    chamber: Optional[str] = None
    state: Optional[str] = None
    party: Optional[str] = None
    is_active: bool
    photo_url: Optional[str] = None
    ai_profile_summary: Optional[str] = None
    sanctions_status: Optional[str] = None
    sanctions_data: Optional[dict] = None
    sanctions_checked_at: Optional[str] = None


# ---------------------------------------------------------------------------
# 5. GET /finance/dashboard/stats
# ---------------------------------------------------------------------------

class FinanceDashboardStats(BaseModel):
    total_institutions: int
    total_filings: int
    total_financials: int
    total_complaints: int
    total_fred_observations: int
    total_press_releases: int
    total_lobbying: int
    total_lobbying_spend: float
    total_contracts: int
    total_contract_value: float
    total_enforcement: int
    total_penalties: float
    total_insider_trades: int
    by_sector: Dict[str, int]


# ---------------------------------------------------------------------------
# 6. GET /influence/stats
# ---------------------------------------------------------------------------

class SectorInfluenceBreakdown(BaseModel):
    lobbying: float
    contracts: float
    enforcement: int

class InfluenceStatsResponse(BaseModel):
    total_lobbying_spend: float
    total_contract_value: float
    total_enforcement_actions: int
    politicians_connected: int
    by_sector: Dict[str, SectorInfluenceBreakdown]


# ---------------------------------------------------------------------------
# 7. GET /search
# ---------------------------------------------------------------------------

class SearchPolitician(BaseModel):
    person_id: str
    name: Optional[str] = None
    state: Optional[str] = None
    party: Optional[str] = None
    chamber: Optional[str] = None
    photo_url: Optional[str] = None

class SearchCompany(BaseModel):
    entity_id: str
    name: Optional[str] = None
    ticker: Optional[str] = None
    sector: str

class SearchResponse(BaseModel):
    politicians: List[SearchPolitician]
    companies: List[SearchCompany]
    query: str


# ---------------------------------------------------------------------------
# 8. POST /claims/verify
# ---------------------------------------------------------------------------

class VerificationEvaluation(BaseModel):
    tier: str
    score: Optional[float] = None
    relevance: Optional[float] = None
    progress: Optional[float] = None
    timing: Optional[float] = None

class VerificationItem(BaseModel):
    """A single claim verification result."""
    claim_id: Optional[int] = None
    text: Optional[str] = None
    evaluation: Optional[VerificationEvaluation] = None
    extracted: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"

class TierCounts(BaseModel):
    strong: int = 0
    moderate: int = 0
    weak: int = 0
    unverified: int = 0

class VerificationResponse(BaseModel):
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_name: Optional[str] = None
    source_url: Optional[str] = None
    claims_extracted: int = 0
    tier_counts: Optional[TierCounts] = None
    verifications: List[VerificationItem] = Field(default_factory=list)
    summary: str = ""
    auth_tier: Optional[str] = None

    class Config:
        extra = "allow"


# ---------------------------------------------------------------------------
# 9. POST /chat/ask  (ChatResponse already exists in routers/chat.py,
#    re-exported here for completeness)
# ---------------------------------------------------------------------------

class ChatActionSchema(BaseModel):
    type: str
    path: Optional[str] = None
    query: Optional[str] = None

class ChatResponseSchema(BaseModel):
    answer: str
    action: Optional[ChatActionSchema] = None
    cached: bool = False


# ---------------------------------------------------------------------------
# 10. GET /stories/latest
# ---------------------------------------------------------------------------

class StoryItem(BaseModel):
    id: int
    title: Optional[str] = None
    slug: Optional[str] = None
    summary: Optional[str] = None
    body: Optional[str] = None
    category: Optional[str] = None
    sector: Optional[str] = None
    entity_ids: Optional[list] = None
    evidence: Optional[dict] = None
    data_sources: Optional[list] = None
    published_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    verification_score: Optional[float] = None
    verification_tier: Optional[str] = None
    verification_data: Optional[dict] = None
    status: Optional[str] = None
    ai_generated: Optional[str] = None  # e.g. "opus", "algorithmic", "claude" — NOT a bool
    data_date_range: Optional[str] = None
    data_freshness_at: Optional[str] = None
    correction_history: Optional[list] = None
    retraction_reason: Optional[str] = None

class StoriesListResponse(BaseModel):
    stories: List[StoryItem]


# ---------------------------------------------------------------------------
# 11. Politics Bills
# ---------------------------------------------------------------------------

class BillSponsorItem(BaseModel):
    bioguide_id: Optional[str] = None
    role: Optional[str] = None
    person_id: Optional[str] = None
    display_name: Optional[str] = None
    party: Optional[str] = None
    state: Optional[str] = None
    photo_url: Optional[str] = None

class BillListItem(BaseModel):
    bill_id: str
    congress: Optional[int] = None
    bill_type: Optional[str] = None
    bill_number: Optional[int] = None
    title: Optional[str] = None
    policy_area: Optional[str] = None
    status_bucket: Optional[str] = None
    latest_action_text: Optional[str] = None
    latest_action_date: Optional[str] = None
    introduced_date: Optional[str] = None
    source_retrieved_at: Optional[str] = None
    sponsors: List[BillSponsorItem] = []

class BillsListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    bills: List[BillListItem]
    source: str = "Congress.gov API"
    dataset_updated_at: Optional[str] = None

class BillDetailResponse(BaseModel):
    bill_id: str
    congress: Optional[int] = None
    bill_type: Optional[str] = None
    bill_number: Optional[int] = None
    title: Optional[str] = None
    policy_area: Optional[str] = None
    status_bucket: Optional[str] = None
    latest_action_text: Optional[str] = None
    latest_action_date: Optional[str] = None
    introduced_date: Optional[str] = None
    congress_url: Optional[str] = None
    summary_text: Optional[str] = None
    summary_source: str = "unavailable"
    source: str = "Congress.gov API"
    source_url: Optional[str] = None
    source_retrieved_at: Optional[str] = None
    source_content_sha256: Optional[str] = None
    source_completeness: Dict[str, bool] = {}
    sponsors: List[BillSponsorItem] = []
    timeline: List[Dict[str, Any]] = []

    class Config:
        extra = "allow"

class BillEnrichmentStats(BaseModel):
    total_bills: int
    with_title: int
    with_summary: int
    with_status_bucket: int
    title_pct: float
    summary_pct: float


# ---------------------------------------------------------------------------
# 12. Politics Votes
# ---------------------------------------------------------------------------

class VoteListItem(BaseModel):
    vote_id: Optional[str] = None
    chamber: Optional[str] = None
    # `session` historically was a string, but Vote.vote_session is an
    # int in the DB (1 / 2 for the two sessions of a Congress). Both
    # are accepted on the wire so old clients that expected a string
    # still work, and the validator stops 500-ing on int responses.
    session: Optional[Union[str, int]] = None
    congress: Optional[int] = None
    question: Optional[str] = None
    result: Optional[str] = None
    date: Optional[str] = None
    bill_id: Optional[str] = None
    bill_title: Optional[str] = None
    yea_count: Optional[int] = None
    nay_count: Optional[int] = None
    not_voting_count: Optional[int] = None
    present_count: Optional[int] = None

    class Config:
        extra = "allow"

class VotesListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    votes: List[VoteListItem]


# ---------------------------------------------------------------------------
# 13. Committees
# ---------------------------------------------------------------------------

class CommitteeItem(BaseModel):
    thomas_id: Optional[str] = None
    name: Optional[str] = None
    chamber: Optional[str] = None
    committee_type: Optional[str] = None
    url: Optional[str] = None
    minority_url: Optional[str] = None
    member_count: int = 0

    class Config:
        extra = "allow"

class CommitteesListResponse(BaseModel):
    total: int
    committees: List[CommitteeItem]


# ---------------------------------------------------------------------------
# 14. Anomalies
# ---------------------------------------------------------------------------

class AnomalyItem(BaseModel):
    id: int
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    anomaly_type: Optional[str] = None
    severity: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    detected_at: Optional[str] = None
    is_acknowledged: bool = False

    class Config:
        extra = "allow"

class AnomaliesListResponse(BaseModel):
    total: int
    anomalies: List[AnomalyItem]


# ---------------------------------------------------------------------------
# 15. Congressional Trades
# ---------------------------------------------------------------------------

class TradeItem(BaseModel):
    id: Optional[int] = None
    person_id: Optional[str] = None
    display_name: Optional[str] = None
    party: Optional[str] = None
    state: Optional[str] = None
    ticker: Optional[str] = None
    asset_description: Optional[str] = None
    trade_type: Optional[str] = None
    amount_range: Optional[str] = None
    trade_date: Optional[str] = None
    disclosure_date: Optional[str] = None

    class Config:
        extra = "allow"

class TradesListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    trades: List[TradeItem]


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

class WatchlistItem(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    entity_name: Optional[str] = None
    sector: Optional[str] = None
    created_at: Optional[str] = None

class WatchlistAddResponse(BaseModel):
    status: str
    id: Optional[int] = None

class WatchlistListResponse(BaseModel):
    total: int
    items: List[WatchlistItem]

class WatchlistCheckResponse(BaseModel):
    watching: bool
    item_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Read-only issue detail
# ---------------------------------------------------------------------------

class IssueSource(BaseModel):
    url: str
    publisher: str
    retrieved_at: str

class IssueSummaryResponse(BaseModel):
    slug: str
    title: str
    summary: Optional[str] = None
    evidence_series_count: int
    bill_count: int

class IssueAgendaMethodology(BaseModel):
    kind: Literal["public_priorities_poll"]
    label: str
    description: str
    community_ranked: Literal[False]
    sample_size: int
    survey_start: str
    survey_end: str
    margin_of_error_points: float
    source_url: str
    publisher: str
    question: str
    tie_break: str
    updated_at: Optional[str] = None

class IssueAgendaItem(BaseModel):
    rank: int
    slug: str
    title: str
    summary: Optional[str] = None
    evidence_note: Optional[str] = None
    evidence_series_count: int
    bill_count: int
    latest_evidence_date: Optional[str] = None
    priority_share: int
    priority_note: str
    community_score: Literal[None] = None

class IssueAgendaResponse(BaseModel):
    total: int
    methodology: IssueAgendaMethodology
    items: List[IssueAgendaItem]

class IssueGeography(BaseModel):
    type: str
    id: str

class IssueEvidenceObservation(BaseModel):
    date: str
    value: float
    source_record_id: Optional[str] = None
    source: IssueSource

class IssueEvidenceSeriesItem(BaseModel):
    key: str
    title: str
    unit: str
    geography: IssueGeography
    source: IssueSource
    observations: List[IssueEvidenceObservation]

class IssueEvidenceResponse(BaseModel):
    issue_slug: str
    total: int
    series: List[IssueEvidenceSeriesItem]

class IssueBillItem(BaseModel):
    bill_id: str
    congress: int
    bill_type: str
    bill_number: int
    title: Optional[str] = None
    policy_area: Optional[str] = None
    phase: Literal["past", "current", "upcoming", "enacted"]
    status_bucket: Optional[str] = None
    status_reason: Optional[str] = None
    latest_action_text: Optional[str] = None
    latest_action_date: Optional[str] = None
    relevance_note: Optional[str] = None
    source: IssueSource

class IssueBillsResponse(BaseModel):
    issue_slug: str
    total: int
    bills: List[IssueBillItem]


# ---------------------------------------------------------------------------
# Read-only Watch video contracts
# ---------------------------------------------------------------------------

class VideoIssueLink(BaseModel):
    slug: str
    title: str

class VideoBillLink(BaseModel):
    bill_id: str
    title: Optional[str] = None

class VideoDelivery(BaseModel):
    mode: Literal["official_embed", "hosted_video", "link_out"]
    provider: Optional[str] = None
    provider_video_id: Optional[str] = None
    canonical_url: str
    poster_url: Optional[str] = None
    source_label: Optional[str] = None
    development_only: bool = False

class VideoAccessibility(BaseModel):
    text_kind: Literal["overview", "transcript"]
    official_transcript_url: str
    official_transcript_label: str
    overview_points: List[str] = Field(default_factory=list)
    development_only: bool = False

class VideoItem(BaseModel):
    video_id: str
    content_origin: Literal["reviewed", "community"] = "reviewed"
    creator_label: str
    caption: str
    transcript: Optional[str] = None
    captions_url: Optional[str] = None
    media_url: str
    delivery: Optional[VideoDelivery] = None
    accessibility: Optional[VideoAccessibility] = None
    published_at: str
    source: IssueSource
    issue: VideoIssueLink
    bills: List[VideoBillLink]
    discussion_post_id: Optional[int] = None
    like_count: int = 0
    discussion_count: int = 0
    liked: bool = False
    saved: bool = False

class VideoInteractionState(BaseModel):
    video_id: str
    like_count: int
    discussion_count: int
    liked: bool
    saved: bool

class VideoInteractionUpdate(BaseModel):
    active: bool

class VideosResponse(BaseModel):
    total: int
    videos: List[VideoItem]
    next_cursor: Optional[str] = None
    has_more: bool = False

class VideoSharePreview(BaseModel):
    video_id: str
    canonical_url: str
    title: str
    description: str
    image_url: Optional[str] = None
    source: IssueSource
