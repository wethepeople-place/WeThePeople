import json

from models.auth_models import User
from models.social_models import DiscussionPost, DiscussionReport
from services.jwt_auth import create_access_token, create_password_reset_token, verify_token
from services.rbac import VALID_ROLES


EMAIL = "testuser@example.com"
ORIGINAL_PASSWORD = "securepassword123"
RESET_PASSWORD = "new-secure-password-456"


def _login(client, password=ORIGINAL_PASSWORD):
    return client.post("/auth/login", json={"email": EMAIL, "password": password})


def test_role_contract_matches_machine_readable_inventory():
    inventory = json.loads(open("config/identity_data_inventory.json", encoding="utf-8").read())
    assert list(VALID_ROLES) == inventory["roles"]


def test_password_reset_invalidates_all_older_access_and_refresh_tokens(client, db_session):
    login = _login(client)
    assert login.status_code == 200
    old_access = login.json()["access_token"]
    old_refresh = login.json()["refresh_token"]
    user = db_session.query(User).filter_by(email=EMAIL).one()
    assert verify_token(old_access)["session_version"] == user.session_version == 1

    reset_token = create_password_reset_token(user.id, user.email, user.session_version)
    reset = client.post("/auth/reset-password", json={"token": reset_token, "new_password": RESET_PASSWORD})
    assert reset.status_code == 200
    db_session.expire_all()
    assert db_session.get(User, user.id).session_version == 2
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {old_access}"}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": old_refresh}).status_code == 401
    replay = client.post(
        "/auth/reset-password",
        json={"token": reset_token, "new_password": "another-password-789"},
    )
    assert replay.status_code == 401
    assert _login(client, RESET_PASSWORD).status_code == 200


def test_privacy_export_requires_password_and_covers_classified_social_data(client, db_session):
    user = db_session.query(User).filter_by(email=EMAIL).one()
    post = DiscussionPost(author_id=user.id, author_label="Test User", body="A public contribution")
    db_session.add(post)
    db_session.flush()
    db_session.add(DiscussionReport(
        reporter_id=user.id, target_type="post", target_id=post.id,
        reason="other", details="private context",
    ))
    db_session.commit()

    token = create_access_token({
        "sub": user.email, "user_id": user.id, "role": user.role,
        "session_version": user.session_version,
    })
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/auth/privacy/export", json={"password": "wrong-password"}, headers=headers).status_code == 403
    exported = client.post("/auth/privacy/export", json={"password": RESET_PASSWORD}, headers=headers)
    assert exported.status_code == 200
    payload = exported.json()
    assert payload["user"]["email"] == EMAIL
    assert payload["classified_records"]["discussion_posts"][0]["body"] == "A public contribution"
    assert payload["classified_records"]["discussion_reports"][0]["details"] == "private context"
    assert "hashed_password" not in str(payload)
    assert "key_hash" not in str(payload)


def test_account_anonymization_is_reauthenticated_bounded_and_invalidates_session(client, db_session):
    user = db_session.query(User).filter_by(email=EMAIL).one()
    user_id = user.id
    token = create_access_token({
        "sub": user.email, "user_id": user.id, "role": user.role,
        "session_version": user.session_version,
    })
    headers = {"Authorization": f"Bearer {token}"}
    rejected = client.post(
        "/auth/privacy/anonymize",
        json={"password": RESET_PASSWORD, "confirmation": "yes"},
        headers=headers,
    )
    assert rejected.status_code == 400

    response = client.post(
        "/auth/privacy/anonymize",
        json={"password": RESET_PASSWORD, "confirmation": "ANONYMIZE MY ACCOUNT"},
        headers=headers,
    )
    assert response.status_code == 200 and response.json()["status"] == "anonymized"
    assert client.get("/auth/me", headers=headers).status_code == 401

    db_session.expire_all()
    anonymized = db_session.get(User, user_id)
    assert anonymized.is_active == 0 and anonymized.session_version == 3
    assert anonymized.email.startswith("deleted-") and anonymized.email.endswith("@anonymized.local")
    assert anonymized.verified_zip is None and anonymized.zip_code is None
    assert anonymized.digest_opt_in == 0 and anonymized.alert_opt_in == 0
    post = db_session.query(DiscussionPost).filter_by(author_id=user_id).one()
    report = db_session.query(DiscussionReport).filter_by(reporter_id=user_id).one()
    assert post.author_label.startswith("Deleted User ")
    assert report.details is None
