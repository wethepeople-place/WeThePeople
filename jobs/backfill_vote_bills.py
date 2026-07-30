"""Create minimal bill shells for stored votes with related-measure metadata."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connectors.congress_votes import backfill_related_bills
from models.database import SessionLocal


def main() -> None:
    session = SessionLocal()
    try:
        created = backfill_related_bills(session)
        print(f"Created {created} vote-sourced bill record(s).")
    finally:
        session.close()


if __name__ == "__main__":
    main()
