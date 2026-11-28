"""Refresh the per-member legislative ``Action`` rows.

The member legislation connector existed before this job was scheduled, which
left the Actions table stale. This job closes that gap with restartable batches.

What it does:
  - Selects a batch of active members, prioritising members that have never
    completed an import and then the stalest successful refreshes.
  - Fetches sponsored and cosponsored bills from Congress.gov.
  - Upserts Action and SourceDocument rows using the connector's natural key.
  - Records coverage only after both feeds succeed for a member.

Cadence: every six hours in restartable batches. A failed member stays eligible
for a later run. ``limit_pages=2`` is the default to bound runtime and API use.

Usage:
    python jobs/sync_member_actions.py
    python jobs/sync_member_actions.py --limit-pages 5
    python jobs/sync_member_actions.py --batch-size 80
    python jobs/sync_member_actions.py --members rashida_tlaib elissa_slotkin
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("sync_member_actions")


def run(
    limit_pages: int = 2,
    person_ids: list[str] | None = None,
    batch_size: int = 80,
) -> int:
    """Run the member-legislation sync. Return 0 unless the whole batch fails."""
    from connectors.congress import API_KEY, ingest_member_legislation

    if not API_KEY:
        log.error("No Congress.gov API key configured (set CONGRESS_API_KEY env). Exiting.")
        return 1

    started_at = time.time()
    try:
        result = ingest_member_legislation(
            limit_pages=limit_pages,
            person_ids=person_ids,
            limit_members=None if person_ids else batch_size,
        )
    except Exception as exc:
        log.exception("ingest_member_legislation raised: %s", exc)
        return 1

    log.info("sync_member_actions finished in %.1fs: %s", time.time() - started_at, result)
    if result["processed_members"] == 0 and result["failed_members"] > 0:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit-pages",
        type=int,
        default=int(os.getenv("WTP_CONGRESS_LIMIT_PAGES", "2")),
        help="Pages of bill results per member and category (default 2).",
    )
    parser.add_argument(
        "--members",
        nargs="*",
        default=None,
        help="Restrict the run to these person_ids.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(os.getenv("WTP_MEMBER_ACTION_BATCH_SIZE", "80")),
        help="Maximum overdue members per run (default 80; ignored with --members).",
    )
    args = parser.parse_args()
    return run(
        limit_pages=args.limit_pages,
        person_ids=args.members,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    raise SystemExit(main())
