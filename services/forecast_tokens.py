"""Short-lived signed references for official election contests.

The token contains only public ballot facts. It never contains the lookup
address, registration information, or a user's selection.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt

from services.jwt_auth import ALGORITHM, SECRET_KEY


def sign_election_contest(payload: dict[str, Any]) -> str:
    body = dict(payload)
    body.update({"purpose": "election_forecast", "exp": datetime.now(timezone.utc) + timedelta(hours=12)})
    return jwt.encode(body, SECRET_KEY, algorithm=ALGORITHM)


def verify_election_contest(token: str) -> dict[str, Any]:
    body = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if body.get("purpose") != "election_forecast":
        raise jwt.InvalidTokenError("wrong token purpose")
    return body
