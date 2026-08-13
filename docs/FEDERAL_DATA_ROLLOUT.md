# Federal civic data rollout

This runbook covers the current Congress roster, committees, committee memberships,
House and Senate roll-call votes, member legislative activity, and the Housing & Rent
HUD Fair Market Rent evidence series. It does not authorize a production write or deploy.

## Required sources and credentials

- Current roster and committees: `unitedstates/congress-legislators` current YAML snapshots (CC0), recorded with URL and SHA-256.
- House votes and member legislative activity: Congress.gov API.
- Senate votes: official Senate.gov XML.
- Housing Fair Market Rents: HUD USER FMR & IL API.
- Rent CPI and average wages: Bureau of Labor Statistics API/public series.

`CONGRESS_API_KEY` or `API_KEY_CONGRESS` must be present. `HUD_API_KEY` must belong to
an account registered for the **FMR & IL API**. A HUD 403 means the token is not
registered for that dataset; do not substitute estimates or silently omit HUD from a
newly generated fixture.

## Staging gate

1. Use an isolated database whose filename contains `staging`:

   ```bash
   export WTP_ENV=staging
   export WTP_DB_URL=sqlite:////app/data/wethepeople-staging.db
   python jobs/rehearse_congress_foundation.py \
     --db-url "$WTP_DB_URL" \
     --report /app/data/congress-foundation-report.json
   ```

2. The rehearsal must pass all pre-write bounds and post-write reconciliation:

   - 500-600 active legislators;
   - 420-450 House members/delegates and 95-105 senators;
   - at least 30 top-level committees and 500 memberships;
   - active database roster equals the source roster;
   - at least 98% of committee memberships link to a tracked member;
   - every source has a URL, byte count, and SHA-256 in the report.

3. Run bounded network samples before a full history load:

   ```bash
   python jobs/sync_votes.py --congress 119 --limit 3
   python jobs/sync_senate_votes.py --congress 119 --session 2 --start 1 --end 2
   python jobs/sync_member_actions.py --limit-pages 1 \
     --members johnny_olszewski_jr angela_d_alsobrooks chris_van_hollen
   ```

4. Generate and validate Housing & Rent only after HUD authorization succeeds:

   ```bash
   python jobs/fetch_housing_rent_fixture.py \
     /app/data/housing-rent-reviewed-staging.json \
     --start-year 2022 --end-year 2025
   python jobs/load_housing_rent_slice.py \
     /app/data/housing-rent-reviewed-staging.json
   ```

5. Verify the staging API and UI:

   - `/politics/people` returns roughly 537 current members, not zero;
   - `/politics/people?q=maryland,` displays the Maryland delegation;
   - `/politics/activity` displays sourced actions and votes;
   - committees display current linked memberships;
   - `/issues/housing-rent` displays three sourced evidence series after HUD loads;
   - source links, timestamps, and honest empty/error states render correctly on desktop and mobile.

## Production approval gate

Before any production data write, obtain an explicit owner approval that names all three:

1. production database backup;
2. federal/HUD data load;
3. application deployment.

Record the current backend commit, frontend deployment, database location, database size,
row counts, and SHA-256 of the backup. Never print API keys into the deployment record.

## Production backup and load order

1. Stop the scheduler, then stop the API so the SQLite backup is transactionally stable.
2. Copy the database to a timestamped, access-restricted backup and calculate SHA-256.
3. Restart the API with the scheduler still stopped; confirm `/health` succeeds.
4. Run the Congress foundation import first and retain its JSON report.
5. Run House votes, Senate votes, and member actions sequentially.
6. Load the reviewed Housing & Rent fixture only if its live HUD fetch and validation passed.
7. Reconcile counts and inspect API responses before restarting the scheduler.
8. Deploy the frontend only after the production API responses are correct.

## Abort and rollback

Abort before continuing if validation bounds fail, linked memberships fall below 98%,
an authoritative source is unavailable, or any endpoint returns inconsistent counts.

For a data-load failure, keep the scheduler stopped, stop the API, preserve the failed
database and reports for diagnosis, restore the checksummed pre-load database backup,
restart the API, and verify health plus pre-load row counts. For a code-only failure,
use `deploy/rollback.sh <previous-commit>` for the backend and promote the previous
Vercel deployment for the frontend. Do not combine a code rollback with a stale database
unless the pre-load backup is also restored.

## Evidence to retain

- source URLs, retrieval time, byte counts, and SHA-256 values;
- staging and production reconciliation reports;
- pre/post row counts for members, committees, memberships, votes, member votes, and actions;
- focused test output and frontend build result;
- backup path, size, hash, restore check, and rollback decision;
- deployment commits and verification timestamps.
