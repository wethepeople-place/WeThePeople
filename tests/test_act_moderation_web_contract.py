from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
ROUTES = (ROOT / "frontend" / "scripts" / "generate-spa-routes.mjs").read_text(encoding="utf-8")
MENU = (ROOT / "frontend" / "src" / "components" / "UserMenu.tsx").read_text(encoding="utf-8")


def test_act_moderation_has_admin_navigation_and_direct_delivery():
    assert '<Route path="/act/moderation" element={<ActModerationPage />} />' in APP
    assert "await writeRoute(['act', 'moderation'], indexHtml)" in ROUTES
    assert "user?.role === 'admin'" in MENU
