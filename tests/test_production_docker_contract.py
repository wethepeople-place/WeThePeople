from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_production_image_packages_canonical_migrations():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY alembic_canonical/ alembic_canonical/" in dockerfile
    assert "COPY alembic-canonical.ini ." in dockerfile
