import json
from pathlib import Path

from services.watch_phase4c_candidate_research import REQUIRED_CLEARANCE, validate_candidate_research

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "watch_phase4c_candidate_research.json"
RESEARCH = json.loads(PATH.read_text(encoding="utf-8"))


def _root(tmp_path, research):
    (tmp_path / "config").mkdir()
    (tmp_path / "docs" / "phase4c").mkdir(parents=True)
    (tmp_path / "config" / PATH.name).write_text(json.dumps(research), encoding="utf-8")
    name = "CANDIDATE_MEDIA_RESEARCH.md"
    (tmp_path / "docs" / "phase4c" / name).write_text((ROOT / "docs" / "phase4c" / name).read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def test_candidate_research_is_valid_bounded_and_fail_closed():
    report = validate_candidate_research(root=ROOT)
    assert report.valid is True and report.error_codes == ()
    assert RESEARCH["acceptance_catalog_unblocked"] is False


def test_shortlist_has_four_stable_official_census_candidates():
    items = RESEARCH["shortlist"]
    assert len(items) == 4 and len({item["candidate_id"] for item in items}) == 4
    assert all(item["publisher"] == "U.S. Census Bureau" and item["issue_fit"] == "housing-rent" for item in items)
    assert all(item["official_page_url"].startswith("https://www.census.gov/") for item in items)
    assert all(item["transcript_url"].startswith("https://www2.census.gov/") for item in items)


def test_transcript_does_not_overclaim_captions_rights_assets_or_posters():
    for item in RESEARCH["shortlist"]:
        assert item["rights_status"] == "requires_item_level_agency_confirmation"
        assert item["accessibility_status"] == "official_transcript_present_captions_unverified"
        assert item["media_asset_status"] == "embedded_third_party_player_no_reusable_asset_authorized"
        assert item["poster_status"] == "not_documented_for_reuse" and item["duration_status"] == "not_verified"
        assert item["catalog_eligible"] is False


def test_clearance_packet_is_complete_and_hybrid_evaluation_is_next():
    assert set(RESEARCH["required_clearance_packet_per_candidate"]) == REQUIRED_CLEARANCE
    assert RESEARCH["next_recommendation"] == "evaluate_under_hybrid_source_policy_and_link_out_until_source_approved"


def test_rights_accessibility_asset_or_catalog_overclaim_fails_closed(tmp_path):
    changed = json.loads(json.dumps(RESEARCH))
    item = changed["shortlist"][0]
    item["rights_status"] = "public_domain"
    item["accessibility_status"] = "captions_verified"
    item["media_asset_status"] = "download_allowed"
    item["catalog_eligible"] = True
    report = validate_candidate_research(root=_root(tmp_path, changed))
    assert {"rights_overclaim", "accessibility_overclaim", "asset_overclaim"} <= set(report.error_codes)


def test_research_did_not_add_media_or_runtime_surface():
    expected = {
        "config/watch_phase4c_candidate_research.json",
        "docs/phase4c/CANDIDATE_MEDIA_RESEARCH.md",
        "services/watch_phase4c_candidate_research.py",
        "tests/test_phase4c_candidate_media_research.py",
    }
    assert all(not path.startswith(("data/", "models/", "routers/", "jobs/", "alembic/", "alembic_canonical/", "frontend/", "mobile/")) for path in expected)
