"""Refresh the authoritative current Congress foundation behind an explicit gate.

The scheduler may invoke this command, but it performs no network request or database
write unless WTP_ENABLE_CONGRESS_FOUNDATION_SYNC=1. Production still requires the
separate backup/load/deploy approval described in docs/FEDERAL_DATA_ROLLOUT.md before
that flag is enabled.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jobs.rehearse_congress_foundation import run


def enabled(environment: str | None, flag: str | None) -> bool:
    return environment in {"staging", "production"} and flag == "1"


def main() -> int:
    environment = (os.getenv("WTP_ENV") or "").strip().lower()
    flag = (os.getenv("WTP_ENABLE_CONGRESS_FOUNDATION_SYNC") or "").strip()
    if not enabled(environment, flag):
        print("Congress foundation sync disabled; set WTP_ENABLE_CONGRESS_FOUNDATION_SYNC=1 in staging or production")
        return 0

    db_url = (os.getenv("WTP_DB_URL") or "").strip()
    if not db_url:
        print("WTP_DB_URL is required when Congress foundation sync is enabled", file=sys.stderr)
        return 2

    report = run(db_url, allow_non_staging=environment == "production")
    report_dir = Path(os.getenv("WTP_SYNC_REPORT_DIR") or ROOT / "runtime_data" / "sync_reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = report_dir / f"congress-foundation-{stamp}.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "report": str(report_path), "active_members": report["active_members"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
