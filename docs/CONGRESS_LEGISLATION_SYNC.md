# Congress legislation synchronization

`jobs/sync_congress_legislation.py` synchronizes the current Congress from the
official Congress.gov v3 API into the local `bills`, `bill_actions`, and
`member_bills_groundtruth` tables.

It retrieves the complete bill index and, for every new or changed bill:

- bill detail and introduction date;
- complete action history and a transparent lifecycle classification;
- sponsor and active cosponsor Bioguide links;
- official CRS summaries;
- CRS legislative subjects and policy area; and
- the latest official text URL.

Each completed bill stores the Congress.gov update timestamp, retrieval
timestamp, endpoint, completeness flags, and a SHA-256 hash of the normalized
source responses in `metadata_json.congress_sync`. API keys are never written to
the database, logs, or reports.

## Restart and failure behavior

The complete bill index is ordered by most recently updated. Unchanged bills
cost no detail requests. Each bill commits atomically, so a failed bill leaves
no partial timeline or sponsorship replacement. The request budget produces a
successful `checkpoint` run; the next run rescans the index and continues from
the first bill that still needs enrichment. Individual source or validation
failures produce a non-zero `partial` run and are listed in the JSON report.

## Staging rehearsal

Use a database whose filename includes `staging`, then start with a bounded
sample:

```powershell
$env:WTP_DB_URL='sqlite:///runtime_data/congress-legislation-staging.db'
$env:CONGRESS_API_KEY='<stored secret>'
python jobs/sync_congress_legislation.py --congress 119 --max-bills 25 --max-requests 200
```

Run the same command again. A healthy idempotency check reports every sampled
bill as `unchanged` and normally uses one index request.

## Production gate

The scheduler entry is inert in staging and production unless
`WTP_ENABLE_CONGRESS_LEGISLATION_SYNC=1`. Enabling that flag, running the first
full synchronization, migrating existing production bill rows, and deploying
the related API/UI changes require separate production approval plus a verified
database backup and rollback image.

The initial backfill may checkpoint because Congress.gov limits API use to
5,000 requests per hour. The six-hour schedule prioritizes recently changed
bills and safely completes the backlog over repeated runs. Steady-state runs
only enrich bills whose Congress.gov `updateDate` changed.
