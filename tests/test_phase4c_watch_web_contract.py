from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend" / "src" / "pages" / "WatchVideoPage.tsx").read_text(encoding="utf-8")
APP = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")


def test_web_watch_has_feed_and_exact_video_routes():
    assert '<Route path="/watch" element={<WatchVideoPage />} />' in APP
    assert '<Route path="/watch/:videoId" element={<WatchVideoPage />} />' in APP
    assert "navigate(`/watch/${id}`, { replace: true })" in PAGE


def test_web_watch_enforces_visibility_driven_one_active_video():
    assert "new IntersectionObserver" in PAGE and "threshold: [0.6]" in PAGE
    assert "activeId === item.video_id" in PAGE
    assert "if (active && !reducedMotion && !manualPause && !document.hidden)" in PAGE
    assert "else node.pause()" in PAGE


def test_web_watch_has_accessible_controls_transcript_and_failure_context():
    for anchor in ("Play", "Pause", "Unmute", "Mute", "Transcript", "Video unavailable", "official evidence remain available"):
        assert anchor in PAGE
    assert "prefers-reduced-motion: reduce" in PAGE


def test_web_watch_links_exact_records_with_return_identity():
    assert "returnToVideoId: item.video_id" in PAGE
    assert "`/issues/${item.issue.slug}`" in PAGE
    assert "`/politics/bill/${bill.bill_id}`" in PAGE
    assert "`/discuss/${item.discussion_post_id}`" in PAGE


def test_web_watch_labels_development_media_and_has_no_upload_surface():
    assert "Development Watch fixture" in PAGE
    assert not any(term in PAGE.lower() for term in ("/upload", "getusermedia", "mediarecorder", "creator account"))
