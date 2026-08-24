from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTES = (ROOT / "frontend" / "scripts" / "generate-spa-routes.mjs").read_text(encoding="utf-8")


def test_forecast_discovery_has_a_direct_pages_route() -> None:
    assert "await writeRoute(['forecasts'], withSocialMetadata(indexHtml" in ROUTES


def test_public_civic_routes_have_static_delivery_and_specific_previews() -> None:
    assert "await writeRoute(['issues', issue.slug]" in ROUTES
    assert "Civic Discussions | WeThePeople.place" in ROUTES
    assert "Community Forecasts | WeThePeople.place" in ROUTES
    assert "Issue Hub | WeThePeople.place" in ROUTES
