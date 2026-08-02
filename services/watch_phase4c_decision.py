"""Read-only validator for the non-operational Phase 4C Watch decision."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_CATALOG_FIELDS = frozenset({
    "video_id", "creator_label", "editorial_caption", "transcript_or_captions", "poster_asset", "media_asset",
    "duration_ms", "width_px", "height_px", "aspect_ratio", "published_at", "publication_state", "availability_state",
    "primary_issue_slug", "official_evidence_source_ids", "related_bill_ids", "discussion_post_id", "rights_basis",
    "rights_holder", "rights_evidence_reference", "allowed_uses", "rights_reviewed_by", "rights_reviewed_at",
    "provenance_source_url", "provenance_retrieved_at", "editorial_reviewed_by", "editorial_reviewed_at",
    "accessibility_reviewed_by", "accessibility_reviewed_at", "poster_alt_text",
})
REPAIRS = frozenset({
    "rights_cleared_three_to_five_item_catalog", "catalog_metadata_and_review_state", "cursor_pagination",
    "web_playable_vertical_feed", "record_driven_navigation_and_return", "private_reviewed_editorial_ingestion",
    "provider_neutral_media_storage", "multi_item_accessibility_performance_and_smoke_tests",
})
FORBIDDEN_SURFACES = frozenset({
    "public_upload", "camera_recording", "open_creator_accounts", "direct_messages", "algorithmic_recommendations",
    "behavioral_profiling", "advertising", "monetization", "production_cloud_credentials", "network_ingestion",
})


@dataclass(frozen=True)
class Phase4CDecisionValidation:
    valid: bool
    error_codes: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self) | {"error_codes": list(self.error_codes)}


def validate_phase4c_decision(*, root: Path = ROOT) -> Phase4CDecisionValidation:
    errors: set[str] = set()
    try:
        contract = json.loads((root / "config" / "watch_phase4c_decision.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Phase4CDecisionValidation(False, ("contract_unreadable",))

    if contract.get("posture") != "network_free_decision_only" or contract.get("runtime_changes_authorized") is not False or contract.get("implementation_status") != "decision_complete_catalog_assets_blocked":
        errors.add("runtime_claimed")
    audit = contract.get("audit", {})
    if audit.get("existing_catalog_size") != 1 or audit.get("local_rights_cleared_civic_media_count") != 0 or audit.get("acceptance_media_eligible") is not False or audit.get("web_surface") != "share_preview_only" or audit.get("pagination") != "none":
        errors.add("audit_drift")
    catalog = contract.get("catalog_contract", {})
    if catalog.get("minimum_published_items") != 3 or catalog.get("maximum_first_slice_items") != 5 or catalog.get("stable_identity_field") != "video_id" or set(catalog.get("required_fields", ())) != REQUIRED_CATALOG_FIELDS:
        errors.add("catalog_drift")
    if catalog.get("generic_flower_sample_allowed_for_acceptance") is not False or catalog.get("one_primary_issue_required") is not True or catalog.get("one_or_more_official_evidence_citations_required") is not True:
        errors.add("catalog_safety_drift")
    cursor = contract.get("cursor_contract", {})
    if cursor.get("ordering") != ["sort_order ASC", "published_at DESC", "video_id ASC"] or cursor.get("cursor_payload_fields") != ["version", "sort_order", "published_at", "video_id"] or cursor.get("signed_or_authenticated") is not True or cursor.get("offset_pagination_allowed") is not False or cursor.get("unknown_or_tampered_cursor_status") != 400:
        errors.add("cursor_drift")
    authority = contract.get("editorial_authority", {})
    required_true = ("private_authenticated_only", "reviewer_must_differ_from_submitter", "publisher_must_be_authorized", "publish_requires_rights_review", "publish_requires_accessibility_review", "publish_requires_provenance_review", "publish_requires_editorial_review", "immutable_audit_event_required")
    if any(authority.get(key) is not True for key in required_true) or authority.get("public_upload_allowed") is not False or authority.get("creator_self_publish_allowed") is not False:
        errors.add("editorial_boundary_drift")
    storage = contract.get("storage_abstraction", {})
    if storage.get("catalog_stores_provider_neutral_asset_key") is not True or storage.get("arbitrary_external_hotlink_production_ready") is not False or storage.get("production_credentials_authorized") is not False or storage.get("network_ingestion_authorized") is not False:
        errors.add("storage_drift")
    migration = contract.get("migration_compatibility", {})
    if migration.get("preserve_video_id") is not True or migration.get("preserve_existing_read_routes") is not True or migration.get("backfill_must_not_invent_rights_or_review_metadata") is not True:
        errors.add("migration_drift")
    decisions = contract.get("decisions", {})
    if set(decisions.get("repair_before_acceptance", ())) != REPAIRS or not FORBIDDEN_SURFACES <= set(decisions.get("defer", ())):
        errors.add("decision_drift")
    first = contract.get("first_approved_implementation_slice", {})
    if not {"three_to_five_rights_cleared_civic_media_assets", "documented_rights_evidence", "posters", "transcripts_or_captions", "official_evidence_links"} <= set(first.get("blocked_until", ())) or "runtime_routes" not in first.get("still_forbids", ()):
        errors.add("slice_boundary_drift")
    guards = contract.get("drift_guards", {})
    if len(guards) != 7 or any(value is not False for value in guards.values()):
        errors.add("unsafe_guard_authorized")
    try:
        doc = (root / "docs" / "phase4c" / "WATCH_DECISION.md").read_text(encoding="utf-8").lower()
    except OSError:
        doc = ""
    if not all(anchor in doc for anchor in ("network-free and non-operational", "three to five", "fails closed", "same `video_id`", "public uploads", "no local rights-cleared civic video")):
        errors.add("document_drift")
    return Phase4CDecisionValidation(not errors, tuple(sorted(errors)))
