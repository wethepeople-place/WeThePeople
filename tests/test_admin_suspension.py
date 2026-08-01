import json

import pytest

from models.auth_models import APIKeyRecord, AuditLog, User
from routers.auth import pwd_context
from services.jwt_auth import create_access_token


ADMIN_EMAIL = "suspension-admin@example.test"
TARGET_EMAIL = "suspension-target@example.test"
PASSWORD = "suspension-password-123"


@pytest.fixture(scope="module", autouse=True)
def suspension_users(db_session):
    for email, role in ((ADMIN_EMAIL, "admin"), (TARGET_EMAIL, "free")):
        if db_session.query(User).filter_by(email=email).first() is None:
            db_session.add(User(
                email=email,
                hashed_password=pwd_context.hash(PASSWORD),
                display_name=email.split("@")[0],
                role=role,
            ))
    db_session.commit()


def _headers(user):
    token = create_access_token({
        "sub": user.email,
        "user_id": user.id,
        "role": user.role,
        "session_version": user.session_version or 1,
    })
    return {"Authorization": f"Bearer {token}"}, token


def test_only_admin_can_suspend_and_self_suspension_is_blocked(client, db_session):
    admin = db_session.query(User).filter_by(email=ADMIN_EMAIL).one()
    target = db_session.query(User).filter_by(email=TARGET_EMAIL).one()
    target_headers, _ = _headers(target)
    denied = client.post(
        f"/auth/admin/users/{admin.id}/suspend",
        json={"reason": "unauthorized attempt"}, headers=target_headers,
    )
    assert denied.status_code == 403

    admin_headers, _ = _headers(admin)
    self_suspend = client.post(
        f"/auth/admin/users/{admin.id}/suspend",
        json={"reason": "should be rejected"}, headers=admin_headers,
    )
    assert self_suspend.status_code == 400


def test_suspension_revokes_sessions_and_keys_and_reactivation_stays_fresh(client, db_session):
    admin = db_session.query(User).filter_by(email=ADMIN_EMAIL).one()
    target = db_session.query(User).filter_by(email=TARGET_EMAIL).one()
    target_headers, old_token = _headers(target)
    old_version = target.session_version or 1
    key = APIKeyRecord(
        user_id=target.id,
        key_hash="a" * 64,
        name="suspension test key",
        scopes='["read"]',
        is_active=1,
    )
    db_session.add(key)
    db_session.commit()

    admin_headers, _ = _headers(admin)
    suspended = client.post(
        f"/auth/admin/users/{target.id}/suspend",
        json={"reason": "Credible account compromise report"}, headers=admin_headers,
    )
    assert suspended.status_code == 200
    assert suspended.json()["is_active"] is False
    assert suspended.json()["session_version"] == old_version + 1
    assert suspended.json()["suspended_at"]
    assert client.get("/auth/me", headers=target_headers).status_code == 401

    db_session.expire_all()
    target = db_session.get(User, target.id)
    key = db_session.get(APIKeyRecord, key.id)
    assert target.is_active == 0
    assert target.suspension_reason == "Credible account compromise report"
    assert key.is_active == 0
    audit = db_session.query(AuditLog).filter_by(
        user_id=admin.id, action="account_suspended", resource_id=str(target.id)
    ).one()
    assert json.loads(audit.details)["revoked_api_keys"] == 1

    reactivated = client.post(
        f"/auth/admin/users/{target.id}/reactivate",
        json={"reason": "Ownership reverified through support"}, headers=admin_headers,
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["session_version"] == old_version + 2
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401

    db_session.expire_all()
    target = db_session.get(User, target.id)
    assert target.is_active == 1
    assert target.suspended_at is None and target.suspension_reason is None
    fresh_headers, _ = _headers(target)
    assert client.get("/auth/me", headers=fresh_headers).status_code == 200
    assert db_session.get(APIKeyRecord, key.id).is_active == 0
    reactivation_audit = db_session.query(AuditLog).filter_by(
        user_id=admin.id, action="account_reactivated", resource_id=str(target.id)
    ).one()
    assert json.loads(reactivation_audit.details)["reason"] == "Ownership reverified through support"


def test_reactivation_refuses_generic_inactive_or_anonymized_accounts(client, db_session):
    admin = db_session.query(User).filter_by(email=ADMIN_EMAIL).one()
    blocked = User(
        email="deleted-suspension-test@anonymized.local",
        hashed_password="ANONYMIZED",
        display_name="Deleted User",
        role="free",
        is_active=0,
    )
    db_session.add(blocked)
    db_session.commit()
    admin_headers, _ = _headers(admin)
    response = client.post(
        f"/auth/admin/users/{blocked.id}/reactivate",
        json={"reason": "must remain deleted"}, headers=admin_headers,
    )
    assert response.status_code == 409
    db_session.refresh(blocked)
    assert blocked.is_active == 0
