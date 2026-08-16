from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
NAV = (ROOT / "frontend" / "src" / "components" / "CivicJourneyNav.tsx").read_text(encoding="utf-8")
PANEL = (ROOT / "frontend" / "src" / "components" / "RepresentativeActPanel.tsx").read_text(encoding="utf-8")
HUB = (ROOT / "frontend" / "src" / "pages" / "ActHubPage.tsx").read_text(encoding="utf-8")
ISSUE_ACTIONS = (ROOT / "frontend" / "src" / "components" / "IssueActionStrip.tsx").read_text(encoding="utf-8")
DISCUSSION = (ROOT / "frontend" / "src" / "pages" / "DiscussionDetailPage.tsx").read_text(encoding="utf-8")
ROUTES = (ROOT / "frontend" / "scripts" / "generate-spa-routes.mjs").read_text(encoding="utf-8")


def test_act_has_navigation_and_static_deep_link_delivery():
    assert '<Route path="/act" element={<ActHubPage />} />' in APP
    assert "{ label: 'ACT', to: '/act' }" in NAV
    assert "await writeRoute(['act'], indexHtml)" in ROUTES
    assert "target_type=video" in ISSUE_ACTIONS and "target_type=issue" in ISSUE_ACTIONS
    assert "ACT on this conversation" in DISCUSSION


def test_act_contact_is_deliberate_private_and_never_auto_sends():
    for anchor in (
        "never sends messages or places calls for you",
        "Copy message",
        "Open {item.label}",
        "I submitted it myself",
        "Receipts are private by default",
    ):
        assert anchor in PANEL
    assert "mailto:" not in PANEL
    assert "private_note: message" not in PANEL


def test_act_hub_uses_moderated_truthful_states_and_disables_legal_enrollment():
    for anchor in (
        "No moderated Circles are public yet",
        "Unreviewed community submissions are never published automatically",
        "Legal pathways are not enabled",
        "will not decide eligibility or enroll plaintiffs",
    ):
        assert anchor in HUB
    assert "Join lawsuit" in HUB
    assert "RSVP privately" in HUB
