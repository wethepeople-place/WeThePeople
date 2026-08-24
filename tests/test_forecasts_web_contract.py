from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTES = (ROOT / "frontend" / "scripts" / "generate-spa-routes.mjs").read_text(encoding="utf-8")


def test_forecast_discovery_has_a_direct_pages_route() -> None:
    assert "await writeRoute(['forecasts'], indexHtml)" in ROUTES
