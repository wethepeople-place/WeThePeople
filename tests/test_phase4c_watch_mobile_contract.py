from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCREEN = (ROOT / "mobile" / "src" / "screens" / "WatchScreen.tsx").read_text(encoding="utf-8")
TYPES = (ROOT / "mobile" / "src" / "api" / "types.ts").read_text(encoding="utf-8")


def test_mobile_treats_official_embed_as_canonical_link_out():
    assert "item.delivery?.mode === 'official_embed'" in SCREEN
    assert "useVideoPlayer(linkOut ? null : item.media_url" in SCREEN
    assert "openExternalUrl(linkOut.canonical_url" in SCREEN
    assert "Open official video" in SCREEN
    assert "official_embed" in TYPES and "canonical_url: string" in TYPES


def test_mobile_labels_overview_accurately_and_links_official_transcript():
    assert "item.accessibility?.text_kind === 'overview' ? 'Overview' : 'Transcript'" in SCREEN
    assert "{narrativeLabel} {narrativeVisible ? 'shown' : 'hidden'}" in SCREEN
    assert "item.accessibility!.official_transcript_url" in SCREEN
    assert "item.accessibility.official_transcript_label" in SCREEN
    assert "Captions {" not in SCREEN
