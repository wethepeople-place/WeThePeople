"""Fail-closed environment or file-backed secret loading.

For ``NAME``, operators may set ``NAME_FILE`` to a root-only mounted file.
The file form takes precedence so secret values do not need to appear in
container environment metadata. A configured but unreadable/empty file is an
operator error, not a reason to fall back to a stale environment value.
"""

from __future__ import annotations

import os
from pathlib import Path


def get_secret(name: str, default: str = "", *, required: bool = False) -> str:
    file_name = os.getenv(f"{name}_FILE", "").strip()
    if file_name:
        try:
            value = Path(file_name).read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise RuntimeError(f"{name}_FILE could not be read") from exc
        if not value:
            raise RuntimeError(f"{name}_FILE is empty")
        return value

    value = os.getenv(name, "").strip()
    if value:
        return value
    if required:
        raise RuntimeError(f"{name} or {name}_FILE must be configured")
    return default
