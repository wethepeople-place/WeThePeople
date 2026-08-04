import json
from pathlib import Path

from services.watch_phase4c_embed_compatibility import DEFER, KEEP, REPAIR, validate_embed_compatibility

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "watch_phase4c_embed_compatibility.json"
AUDIT = json.loads(PATH.read_text(encoding="utf-8"))


def _root(tmp_path, audit):
    (tmp_path / "config").mkdir()
    (tmp_path / "frontend" / "src" / "pages").mkdir(parents=True)
    (tmp_path / "mobile" / "src" / "screens").mkdir(parents=True)
    (tmp_path / "config" / PATH.name).write_text(json.dumps(audit), encoding="utf-8")
    (tmp_path / "frontend" / "src" / "pages" / "WatchVideoPage.tsx").write_text("IntersectionObserver threshold: [0.6] document.hidden", encoding="utf-8")
    (tmp_path / "mobile" / "src" / "screens" / "WatchScreen.tsx").write_text("useVideoPlayer(item.media_url itemVisiblePercentThreshold: 60 AppState", encoding="utf-8")
    return tmp_path


def test_embed_compatibility_audit_is_valid_and_non_operational():
    report = validate_embed_compatibility(root=ROOT)
    assert report.valid is True and report.error_codes == ()
    assert AUDIT["embed_adapter_authorized"] is False and AUDIT["production_playback_enabled"] is False


def test_keep_repair_and_defer_sets_are_complete():
    assert set(AUDIT["keep"]) == KEEP
    assert set(AUDIT["repair_before_embed_adapter"]) == REPAIR
    assert set(AUDIT["defer"]) == DEFER


def test_web_decision_is_consent_gated_visible_and_platform_compliant():
    web = AUDIT["web_decision"]
    assert web["load_before_consent"] is False and web["autoplay_before_consent"] is False
    assert web["maximum_simultaneously_playing"] == 1
    assert web["player_controls_visible"] is True and web["branding_preserved"] is True
    assert web["overlay_over_player_allowed"] is False and web["transcript_outside_player"] is True
    assert web["required_referrer_policy"] == "strict-origin-when-cross-origin"
    assert web["privacy_enhanced_host"] == "www.youtube-nocookie.com"


def test_mobile_and_credentials_remain_deferred():
    mobile = AUDIT["mobile_decision"]
    assert mobile["current_expo_video_adapter_compatible_with_youtube"] is False
    assert mobile["current_webview_dependency_present"] is False
    assert mobile["default_for_embed_sources"] == "canonical_link_out"
    credentials = AUDIT["no_credential_path"]
    assert credentials["youtube_data_api_used"] is False and credentials["credentials_authorized"] is False


def test_weakened_privacy_player_or_credential_boundaries_fail_closed(tmp_path):
    changed = json.loads(json.dumps(AUDIT))
    changed["web_decision"]["load_before_consent"] = True
    changed["web_decision"]["overlay_over_player_allowed"] = True
    changed["web_decision"]["required_referrer_policy"] = "no-referrer"
    changed["no_credential_path"]["credentials_authorized"] = True
    report = validate_embed_compatibility(root=_root(tmp_path, changed))
    assert {"web_safety_drift", "web_platform_drift", "credential_boundary_drift"} <= set(report.error_codes)


def test_audit_slice_adds_no_runtime_or_embed_adapter():
    paths = {
        "config/watch_phase4c_embed_compatibility.json",
        "docs/phase4c/EMBED_COMPATIBILITY_AUDIT.md",
        "services/watch_phase4c_embed_compatibility.py",
        "tests/test_phase4c_embed_compatibility.py",
    }
    assert all(not path.startswith(("models/", "routers/", "jobs/", "alembic/", "alembic_canonical/", "frontend/", "mobile/")) for path in paths)
