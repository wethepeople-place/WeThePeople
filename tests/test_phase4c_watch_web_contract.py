from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend" / "src" / "pages" / "WatchVideoPage.tsx").read_text(encoding="utf-8")
PROVIDERS = (ROOT / "frontend" / "src" / "features" / "watch" / "providers.ts").read_text(encoding="utf-8")
APP = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
VITE_CONFIG = (ROOT / "frontend" / "vite.config.ts").read_text(encoding="utf-8")
PAGES_WORKFLOW = (ROOT / ".github" / "workflows" / "deploy-app-pages.yml").read_text(encoding="utf-8")
PACKAGE = (ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
ROUTE_GENERATOR = (ROOT / "frontend" / "scripts" / "generate-spa-routes.mjs").read_text(encoding="utf-8")


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
    for anchor in ("Play", "Pause", "Unmute", "Mute", "Overview", "Transcript", "Video unavailable", "official evidence remain available"):
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


def test_web_watch_local_api_target_is_loaded_from_the_repository_root():
    assert "loadEnv(mode, path.resolve(__dirname, '..'), 'WTP_')" in VITE_CONFIG


def test_embed_is_server_authorized_and_development_remains_explicit_opt_in():
    assert "import.meta.env.DEV && import.meta.env.VITE_ENABLE_DEVELOPMENT_WATCH_EMBED === 'true'" in PAGE
    assert "item.delivery" in PAGE and "delivery?.mode === 'official_embed'" in PAGE
    assert "getOfficialEmbedUrl(delivery)" in PAGE
    assert "-Zfh6IKiJ4s" not in PAGE and "housing-rent-why-rents-move" not in PAGE


def test_development_embed_is_consent_gated_privacy_enhanced_and_unloaded_when_inactive():
    for anchor in (
        "playerLoaded = active && consented",
        'referrerPolicy="strict-origin-when-cross-origin"',
        "Load official video",
        "Watch at the official source instead",
        "LinkOutCard",
        "getProviderPrivacyUrl(provider)",
    ):
        assert anchor in PAGE
    assert "OfficialEmbedCard" in PAGE and "Transcript" in PAGE


def test_cross_provider_urls_are_validated_and_never_accept_arbitrary_html():
    for provider in ("youtube", "tiktok", "facebook"):
        assert provider in PROVIDERS
    for anchor in ("youtube-nocookie.com/embed/", "tiktok.com/player/v1/", "facebook.com/plugins/video.php"):
        assert anchor in PROVIDERS
    assert "new URL(delivery.canonical_url)" in PROVIDERS
    assert "PROVIDER_IDS[provider].test" in PROVIDERS
    assert "dangerouslySetInnerHTML" not in PAGE + PROVIDERS


def test_direct_watch_identity_fetch_and_github_pages_fallback_are_present():
    assert "encodeURIComponent(videoId)" in PAGE
    assert "This civic video is unavailable." in PAGE
    assert "cp dist/index.html dist/404.html" in PAGES_WORKFLOW
    assert '"postbuild": "node scripts/generate-spa-routes.mjs"' in PACKAGE
    assert "await writeRoute(['watch'], indexHtml)" in ROUTE_GENERATOR
    assert "await writeRoute(['watch', video.video_id], html)" in ROUTE_GENERATOR
    assert "og:title" in ROUTE_GENERATOR and "og:description" in ROUTE_GENERATOR


def test_production_embed_copy_is_not_mislabeled_as_development():
    assert "Official source video" in PAGE
    assert "Development-only official embed test" not in PAGE


def test_watch_poc_has_provider_position_and_scroll_orientation_cues():
    for anchor in ("Reviewed source", "Video ${position} of ${total}", "Scroll for next video", "aspect-[9/16]", 'aria-label="Civic video feed"'):
        assert anchor in PAGE
    assert "motion-safe:animate-bounce" in PAGE


def test_official_transcript_is_record_driven_and_editorial_text_is_labeled_overview():
    assert "accessibility?.text_kind === 'overview' ? 'Overview' : 'Transcript'" in PAGE
    assert "accessibility.official_transcript_url" in PAGE
    assert "accessibility.official_transcript_label" in PAGE
