"""Fail-closed validator for the non-operational Phase 4C embed audit."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEEP = frozenset({
    "stable_video_id_and_exact_url", "sixty_percent_visibility_activation", "one_active_item",
    "pause_inactive_items", "web_document_visibility_pause", "mobile_focus_and_app_state_pause",
    "reduced_motion_gate", "manual_playback_affordance", "transcript_and_evidence_fallback",
    "exact_issue_bill_discussion_source_and_return_navigation", "loading_empty_error_states",
})
REPAIR = frozenset({
    "discriminated_delivery_mode_and_provider_reference", "click_to_load_privacy_gate",
    "privacy_enhanced_youtube_origin", "no_autoplay_before_user_consent", "muted_visible_autoplay_only_after_consent",
    "youtube_referrer_identity_not_suppressed", "official_player_controls_and_branding_preserved",
    "no_overlay_over_player_view_or_controls", "minimum_player_viewport_200_by_200",
    "single_loaded_or_playing_embed_budget", "iframe_api_lifecycle_and_failure_detection",
    "transcript_panel_outside_player_bounds", "transcript_not_mislabeled_as_captions",
    "poster_or_text_card_rights_basis", "canonical_link_out_on_unavailable_or_unconsented",
    "per_item_caption_or_transcript_gate", "embed_terms_and_source_approval_expiry_check",
    "web_keyboard_and_focus_order", "privacy_notice_and_policy_link",
})
DEFER = frozenset({
    "mobile_inline_youtube_webview", "youtube_data_api", "api_credentials", "channel_or_playlist_ingestion",
    "automatic_thumbnail_fetch", "thumbnail_caching", "custom_player_chrome", "player_overlays",
    "background_playback", "preloading_inactive_embeds", "production_source_approval", "production_playback",
})


@dataclass(frozen=True)
class EmbedCompatibilityValidation:
    valid: bool
    error_codes: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self) | {"error_codes": list(self.error_codes)}


def validate_embed_compatibility(*, root: Path = ROOT) -> EmbedCompatibilityValidation:
    errors: set[str] = set()
    try:
        audit = json.loads((root / "config" / "watch_phase4c_embed_compatibility.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return EmbedCompatibilityValidation(False, ("audit_unreadable",))
    if audit.get("posture") != "network_free_decision_only" or audit.get("runtime_changes_authorized") is not False or audit.get("embed_adapter_authorized") is not False or audit.get("production_playback_enabled") is not False:
        errors.add("operational_boundary_drift")
    if set(audit.get("keep", ())) != KEEP or set(audit.get("repair_before_embed_adapter", ())) != REPAIR or set(audit.get("defer", ())) != DEFER:
        errors.add("decision_drift")
    evidence = audit.get("platform_evidence", {})
    if not all(str(evidence.get(key, "")).startswith("https://") for key in ("embed_help", "developer_policies", "minimum_functionality", "player_parameters")) or not evidence.get("reviewed_at"):
        errors.add("evidence_drift")
    web = audit.get("web_decision", {})
    required_web_false = ("current_native_video_adapter_compatible_with_youtube", "load_before_consent", "autoplay_before_consent", "inactive_iframe_preload", "overlay_over_player_allowed")
    required_web_true = ("player_controls_visible", "branding_preserved", "transcript_outside_player")
    if any(web.get(key) is not False for key in required_web_false) or any(web.get(key) is not True for key in required_web_true):
        errors.add("web_safety_drift")
    if web.get("maximum_simultaneously_playing") != 1 or min(web.get("minimum_width_px", 0), web.get("minimum_height_px", 0)) < 200 or web.get("required_referrer_policy") != "strict-origin-when-cross-origin" or web.get("privacy_enhanced_host") != "www.youtube-nocookie.com":
        errors.add("web_platform_drift")
    mobile = audit.get("mobile_decision", {})
    if mobile.get("current_expo_video_adapter_compatible_with_youtube") is not False or mobile.get("current_webview_dependency_present") is not False or mobile.get("default_for_embed_sources") != "canonical_link_out" or len(mobile.get("inline_embed_deferred_until", ())) != 6:
        errors.add("mobile_boundary_drift")
    credentials = audit.get("no_credential_path", {})
    if credentials.get("static_official_iframe_requires_api_key") is not False or credentials.get("youtube_data_api_used") is not False or credentials.get("credentials_authorized") is not False or credentials.get("high_volume_or_api_use_requires_new_review") is not True:
        errors.add("credential_boundary_drift")
    first = audit.get("first_implementation_slice", {})
    if first.get("authorized") is not False or first.get("requires_separate_user_authority") is not True or not {"production_playback", "media_or_thumbnail_download", "api_credentials"} <= set(first.get("still_forbids", ())):
        errors.add("implementation_boundary_drift")
    try:
        web_source = (root / "frontend" / "src" / "pages" / "WatchVideoPage.tsx").read_text(encoding="utf-8")
        mobile_source = (root / "mobile" / "src" / "screens" / "WatchScreen.tsx").read_text(encoding="utf-8")
    except OSError:
        web_source = mobile_source = ""
    if "IntersectionObserver" not in web_source or "threshold: [0.6]" not in web_source or "document.hidden" not in web_source:
        errors.add("web_audit_basis_drift")
    if "useVideoPlayer(item.media_url" not in mobile_source or "itemVisiblePercentThreshold: 60" not in mobile_source or "AppState" not in mobile_source:
        errors.add("mobile_audit_basis_drift")
    return EmbedCompatibilityValidation(not errors, tuple(sorted(errors)))
