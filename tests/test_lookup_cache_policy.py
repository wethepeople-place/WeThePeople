from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware.security import SecurityHeadersMiddleware


def test_representative_lookups_are_never_publicly_cached():
    app = FastAPI()

    @app.get("/lookup/{zip_code}")
    def lookup(zip_code: str):
        return {"zip_code": zip_code}

    @app.get("/v1/lookup/{zip_code}")
    def versioned_lookup(zip_code: str):
        return {"zip_code": zip_code}

    app.add_middleware(SecurityHeadersMiddleware)
    client = TestClient(app)

    for path in ("/lookup/21136", "/v1/lookup/21136"):
        response = client.get(path)
        assert response.headers["cache-control"] == "no-store, no-cache, must-revalidate, max-age=0"
        assert response.headers["pragma"] == "no-cache"
