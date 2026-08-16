from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTES = (ROOT / "frontend" / "scripts" / "generate-spa-routes.mjs").read_text(encoding="utf-8")


def test_discuss_has_a_static_deep_link_route() -> None:
    assert "await writeRoute(['discuss'], indexHtml)" in ROUTES
