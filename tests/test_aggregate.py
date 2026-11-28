"""Tests for sector and cross-sector /aggregate endpoints."""

import pytest


SECTORS = [
    "finance", "health", "tech", "energy", "transportation", "defense",
    "chemicals", "agriculture", "telecom", "education",
]


@pytest.mark.parametrize("sector", SECTORS)
def test_aggregate_enforcement_200(client, sector):
    """Enforcement aggregate for each sector returns 200."""
    r = client.get(f"/aggregate/{sector}/enforcement")
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "actions" in data
    assert isinstance(data["actions"], list)


@pytest.mark.parametrize("sector", SECTORS)
def test_aggregate_lobbying_200(client, sector):
    """Lobbying aggregate for each sector returns 200."""
    r = client.get(f"/aggregate/{sector}/lobbying")
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "filings" in data
    assert isinstance(data["filings"], list)


@pytest.mark.parametrize("sector", SECTORS)
def test_aggregate_contracts_200(client, sector):
    """Contracts aggregate for each sector returns 200."""
    r = client.get(f"/aggregate/{sector}/contracts")
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "contracts" in data
    assert isinstance(data["contracts"], list)


def test_aggregate_enforcement_empty_results(client):
    """Enforcement with no data returns total=0 and empty actions list."""
    r = client.get("/aggregate/finance/enforcement")
    data = r.json()
    # With no enforcement data seeded, total should be 0
    assert data["total"] == 0
    assert data["actions"] == []


def test_aggregate_lobbying_respects_limit(client):
    """Lobbying endpoint respects limit param."""
    r = client.get("/aggregate/tech/lobbying", params={"limit": 1})
    assert r.status_code == 200
    data = r.json()
    assert len(data["filings"]) <= 1



@pytest.mark.parametrize(
    ("kind", "result_key"),
    [("enforcement", "actions"), ("lobbying", "filings"), ("contracts", "contracts")],
)
def test_cross_sector_aggregate_200(client, kind, result_key):
    response = client.get(f"/aggregate/all/{kind}", params={"limit": 5})
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert result_key in data
    assert isinstance(data[result_key], list)
    assert len(data[result_key]) <= 5
