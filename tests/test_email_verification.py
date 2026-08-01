import hashlib
from datetime import datetime, timedelta, timezone

import pytest

from models.auth_models import AuditLog, EmailVerificationToken, User
from routers.auth import pwd_context
from services.jwt_auth import create_access_token


EMAIL = "email-verification@example.test"
PASSWORD = "verification-password-123"
TOKEN_ONE = "first-email-verification-token-with-enough-entropy-000001"
TOKEN_TWO = "second-email-verification-token-with-enough-entropy-00002"


@pytest.fixture(scope="module", autouse=True)
def verification_user(db_session):
    user = db_session.query(User).filter_by(email=EMAIL).first()
    if user is None:
        db_session.add(User(
            email=EMAIL,
            hashed_password=pwd_context.hash(PASSWORD),
            display_name="Verification User",
            role="free",
        ))
        db_session.commit()


def _auth_headers(db_session):
    user = db_session.query(User).filter_by(email=EMAIL).one()
    token = create_access_token({
        "sub": user.email,
        "user_id": user.id,
        "role": user.role,
        "session_version": user.session_version or 1,
    })
    return {"Authorization": f"Bearer {token}"}


def test_request_requires_auth_and_stores_only_a_hash(client, db_session, monkeypatch):
    sent = []
    monkeypatch.setenv("WTP_EMAIL_VERIFICATION_DELIVERY_ENABLED", "1")
    monkeypatch.setattr("routers.auth.secrets.token_urlsafe", lambda _size: TOKEN_ONE)
    monkeypatch.setattr("services.email.send_email", lambda **kwargs: sent.append(kwargs) or True)

    assert client.post("/auth/email-verification/request").status_code == 401
    response = client.post("/auth/email-verification/request", headers=_auth_headers(db_session))
    assert response.status_code == 200
    assert TOKEN_ONE not in response.text

    record = db_session.query(EmailVerificationToken).filter_by(
        token_hash=hashlib.sha256(TOKEN_ONE.encode()).hexdigest()
    ).one()
    assert record.consumed_at is None
    assert record.expires_at is not None
    assert sent and TOKEN_ONE in sent[0]["html"]
    assert db_session.query(AuditLog).filter_by(
        user_id=record.user_id, action="email_verification_sent"
    ).count() == 1


def test_disabled_delivery_preserves_existing_token_and_sends_nothing(
    client, db_session, monkeypatch
):
    monkeypatch.setenv("WTP_EMAIL_VERIFICATION_DELIVERY_ENABLED", "0")
    monkeypatch.setattr(
        "services.email.send_email",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("delivery must remain disabled")),
    )

    response = client.post("/auth/email-verification/request", headers=_auth_headers(db_session))
    assert response.status_code == 200
    db_session.expire_all()
    first = db_session.query(EmailVerificationToken).filter_by(
        token_hash=hashlib.sha256(TOKEN_ONE.encode()).hexdigest()
    ).one()
    assert first.consumed_at is None


def test_new_delivered_request_revokes_previous(client, db_session, monkeypatch):
    monkeypatch.setenv("WTP_EMAIL_VERIFICATION_DELIVERY_ENABLED", "1")
    monkeypatch.setattr("routers.auth.secrets.token_urlsafe", lambda _size: TOKEN_TWO)
    monkeypatch.setattr("services.email.send_email", lambda **_kwargs: True)
    response = client.post("/auth/email-verification/request", headers=_auth_headers(db_session))
    assert response.status_code == 200
    db_session.expire_all()
    first = db_session.query(EmailVerificationToken).filter_by(
        token_hash=hashlib.sha256(TOKEN_ONE.encode()).hexdigest()
    ).one()
    assert first.consumed_at is not None


def test_confirm_is_single_use_and_updates_profile(client, db_session):
    confirm = client.post("/auth/email-verification/confirm", json={"token": TOKEN_TWO})
    assert confirm.status_code == 200
    assert confirm.json() == {"ok": True, "email_verified": True}

    replay = client.post("/auth/email-verification/confirm", json={"token": TOKEN_TWO})
    assert replay.status_code == 400
    db_session.expire_all()
    user = db_session.query(User).filter_by(email=EMAIL).one()
    assert user.email_verified_at is not None
    assert db_session.query(AuditLog).filter_by(user_id=user.id, action="email_verified").count() == 1

    profile = client.get(
        "/auth/me", headers=_auth_headers(db_session)
    )
    assert profile.status_code == 200
    assert profile.json()["email_verified"] is True


def test_expired_token_is_rejected(client, db_session):
    user = db_session.query(User).filter_by(email=EMAIL).one()
    raw = "expired-email-verification-token-with-enough-entropy-0003"
    db_session.add(EmailVerificationToken(
        user_id=user.id,
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    ))
    db_session.commit()
    response = client.post("/auth/email-verification/confirm", json={"token": raw})
    assert response.status_code == 400
