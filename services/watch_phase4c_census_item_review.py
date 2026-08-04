"""Fail-closed validator for the Census registry-only approval decision."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_BLOCKERS = frozenset()
REQUIRED_RECONSIDERATION = frozenset({
    "separate_user_authority_for_production_playback",
})


@dataclass(frozen=True)
class CensusItemReviewValidation:
    valid: bool
    error_codes: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self) | {"error_codes": list(self.error_codes)}


def _https(value: object) -> bool:
    parsed = urlparse(value) if isinstance(value, str) else None
    return bool(parsed and parsed.scheme == "https" and parsed.hostname)


def validate_census_item_review(*, root: Path = ROOT) -> CensusItemReviewValidation:
    errors: set[str] = set()
    try:
        review = json.loads((root / "config" / "watch_phase4c_census_item_review.json").read_text(encoding="utf-8"))
        registry = json.loads((root / "config" / "watch_phase4c_source_registry.json").read_text(encoding="utf-8"))
        fixture = json.loads((root / "data" / "watch_housing_rent.json").read_text(encoding="utf-8"))
        page = (root / "frontend" / "src" / "pages" / "WatchVideoPage.tsx").read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError):
        return CensusItemReviewValidation(False, ("review_inputs_unreadable",))

    if review.get("posture") != "registry_approval_only_no_production_playback":
        errors.add("review_posture_drift")
    record = review.get("record", {})
    if record.get("video_id") != "housing-rent-why-rents-move" or record.get("provider_video_id") != "-Zfh6IKiJ4s":
        errors.add("item_identity_drift")
    if not all(_https(record.get(key)) for key in ("canonical_url", "official_page_url", "official_transcript_url")):
        errors.add("item_evidence_url_invalid")

    evidence = review.get("evidence", {})
    evidence_urls = [value for key, value in evidence.items() if key.endswith("_url")]
    if not evidence.get("census_page_embeds_exact_provider_video") or evidence.get("youtube_verified_publisher") != "U.S. Census Bureau":
        errors.add("official_identity_unverified")
    if evidence.get("youtube_captions_status") != "unavailable" or evidence.get("checked_in_transcript_status") != "editorial_summary_labeled_overview":
        errors.add("accessibility_evidence_drift")
    if not evidence.get("official_transcript_present") or evidence.get("official_transcript_link_exposed") is not True or evidence.get("google_privacy_policy_link_in_consent_notice") is not True or not evidence_urls or not all(_https(url) for url in evidence_urls):
        errors.add("evidence_incomplete")

    gates = review.get("gate_results", {})
    if gates.get("privacy_policy_link_in_consent_notice") != "pass" or gates.get("per_item_captions_or_full_transcript") != "pass_via_official_transcript_link" or gates.get("production_source_registry_state") != "pass_approved_non_operational":
        errors.add("failed_gate_weakened")
    if set(review.get("blockers", ())) != REQUIRED_BLOCKERS or set(review.get("next_reconsideration_requires", ())) != REQUIRED_RECONSIDERATION:
        errors.add("blocker_contract_drift")
    if review.get("recommendation") != "registry_approved_production_disabled" or review.get("required_fallback") != "link_out":
        errors.add("recommendation_not_fail_closed")
    if review.get("registry_mutation_authorized") is not True:
        errors.add("registry_authority_missing")
    forbidden_true = ("production_playback_authorized", "credentials_authorized", "downloads_authorized", "publication_authorized")
    if any(review.get(key) is not False for key in forbidden_true):
        errors.add("operational_boundary_drift")

    source = next((item for item in registry.get("sources", ()) if item.get("source_id") == "us-census-bureau"), {})
    if source.get("source_state") != "approved" or source.get("allowed_delivery_modes") != ["official_embed", "link_out"] or registry.get("production_media_enabled") is not False or registry.get("runtime_changes_authorized") is not False:
        errors.add("registry_state_drift")
    source_evidence = source.get("evidence", {})
    if source_evidence.get("official_channel_reference") != evidence.get("youtube_verified_channel") or not all(source_evidence.get(key) for key in ("embed_terms_url", "embed_terms_reviewed_at", "privacy_reviewed_at")):
        errors.add("registry_approval_evidence_missing")
    if source.get("accessibility", {}).get("captions_or_transcript_required") is not True or source.get("privacy", {}).get("reviewed_at") is None:
        errors.add("registry_approval_guards_missing")
    video = next((item for item in fixture.get("videos", ()) if item.get("video_id") == record.get("video_id")), {})
    accessibility = video.get("accessibility", {})
    if video.get("transcript") == record.get("official_transcript_url") or len(video.get("transcript", "")) > 1000 or accessibility.get("text_kind") != "overview" or accessibility.get("official_transcript_url") != record.get("official_transcript_url"):
        errors.add("fixture_transcript_assumption_drift")
    if "policies.google.com/privacy" not in page or "official_transcript_url" not in page:
        errors.add("remediation_ui_missing")

    return CensusItemReviewValidation(not errors, tuple(sorted(errors)))
