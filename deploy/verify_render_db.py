"""Fail closed unless the restored Render SQLite database is healthy."""

from pathlib import Path
import os
import sqlite3


def database_path() -> Path:
    url = os.environ.get("WTP_DB_URL", "")
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise SystemExit("WTP_DB_URL must point to a file-backed SQLite database")
    raw = url[len(prefix) :]
    path = Path(raw)
    if not path.is_absolute():
        path = Path("/app") / path
    return path


path = database_path()
if not path.is_file():
    raise SystemExit(f"Restored database is missing: {path}")

connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True, timeout=30)
try:
    result = connection.execute("PRAGMA integrity_check").fetchone()[0]
finally:
    connection.close()

if result != "ok":
    raise SystemExit(f"SQLite integrity_check failed: {result}")

print(f"Verified restored SQLite database: {path} ({path.stat().st_size} bytes)")
