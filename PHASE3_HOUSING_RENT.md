# Phase 3: Housing & Rent civic-data slice

This document freezes the first Phase 3 data contract before ingestion code or
schema changes are added. The goal is one trustworthy, inspectable slice—not a
topic-wide crawl or a new product surface.

## Fixed scope

- Issue identity: `housing-rent`
- Validation geography: ZIP `49001`
- Evidence series: HUD Fair Market Rent and BLS wage data
- Legislation: seven curated bills from the 119th Congress
- People: sponsors and matched cosponsors identified by bioguide ID
- Committees: referrals and current membership identified by Thomas ID

The machine-readable constants and status mapping live in
`jobs/housing_rent_contract.py`. Tests in `tests/test_housing_rent_contract.py`
prevent accidental scope expansion or provenance weakening.

## Existing model inventory

| Need | Existing structure | Gap before ingestion |
|---|---|---|
| Issue | None | Add a first-class issue record keyed by `housing-rent`. |
| Evidence series | None | Add series/observation records with unit, geography, source URL, observation date, and retrieval time. |
| Bill | `models.database.Bill` | Add an issue relationship and normalized provenance; `metadata_json` is not the public contract. |
| Bill timeline | `models.database.BillAction` | Actions are usable, but committee referrals contain only a free-text committee name. Add a canonical Thomas ID link when known. |
| Sponsor/cosponsor | `MemberBillGroundTruth` plus `TrackedMember` | Canonical bioguide ID, role, source, and fetch time already exist. Unmatched people must remain visible by identifier and must never be guessed. |
| Committee | `Committee` and `CommitteeMembership` | Canonical Thomas IDs and official committee URLs already exist. Membership source/retrieval metadata must be exposed with the slice. |
| General provenance | `SourceDocument` | It has URL, publisher, retrieval time, and content hash, but bills and evidence observations do not currently reference it. |
| Exact delegation | `/lookup/49001` contract test | Already proves Bill Huizenga plus Senators Elissa Slotkin and Gary Peters, and links Huizenga to HSBA. |

## Curated legislation

Only these records belong to the first slice:

- `hr1-119` — One Big Beautiful Bill Act; only its housing-credit provision is relevant.
- `hr6644-119` — Housing for the 21st Century Act.
- `s968-119` — Rent Relief Act of 2025.
- `hr6124-119` and `s3207-119` — End Rent Fixing Act companion bills.
- `hr2725-119` and `s1515-119` — Affordable Housing Credit Improvement Act companion bills.

Selection is editorial and explicit. Congress.gov topic search is not used as
an automated relevance judgment.

## Status mapping

- `past`: enacted or otherwise conclusively resolved.
- `current`: passed at least one chamber, or has substantive committee activity
  such as a hearing, markup, or report.
- `upcoming`: introduced or routinely referred with no later substantive work.

A routine referral alone is not “active committee work.” Unknown status text
must fail closed for human review rather than being silently assigned.

## Required public provenance

Every evidence series, observation, bill, action, sponsor/cosponsor
relationship, committee, and membership returned by the slice must resolve to:

- an HTTPS source URL;
- a named publisher/source;
- a retrieval timestamp;
- stable source identifiers where the publisher provides them.

Allowed primary authorities for this slice are Congress.gov, official
committee sites, HUD, and BLS. The CC0 `unitedstates/congress-legislators`
dataset is allowed for identity and committee-roster normalization with its
dataset URL and retrieval time preserved.

## Implemented schema checkpoint

Migration `housing_rent_slice_001` adds the minimum issue, evidence-series,
evidence-observation, issue-to-bill, and bill-to-committee-referral structures.
The models reuse the existing bill, bill-action, committee, and source-document
tables; no parallel civic database was created. Normalized source references
are required for every evidence series, observation, issue-bill link, and
committee referral.

## Local fixture loader

`jobs/load_housing_rent_slice.py` validates and idempotently loads a reviewed
JSON fixture. It requires exactly the two evidence series and seven curated
bills, normalized HTTPS sources with publishers and retrieval timestamps,
canonical bioguide IDs for people, and Thomas IDs for committee referrals.
Unknown scope is rejected before a database write.

```bash
python -m jobs.load_housing_rent_slice path/to/reviewed-fixture.json
```

The loader performs no network calls and reads no credentials. It upserts into
the canonical source, bill, bill-action, member-bill, and committee tables plus
the Phase 3 issue tables. Re-running the same fixture is safe.

The fetch adapters below produce the reviewed loader format. Network access
and credentials remain optional during tests and clean-clone boot.

## Bounded fixture generation

`jobs/fetch_housing_rent_fixture.py` builds loader-compatible JSON from only
the reviewed sources. It makes no calls unless invoked directly.

```bash
HUD_API_KEY=... CONGRESS_API_KEY=... \
python -m jobs.fetch_housing_rent_fixture ./housing-rent.review.json \
  --start-year 2019 --end-year 2026
```

`BLS_API_KEY` is optional for the low-volume public API. The generator makes
four Congress.gov requests per curated bill (detail, actions, cosponsors, and
committees), HUD state-data requests only for the selected years, and one BLS
time-series request. The output must be reviewed before passing it to the local
loader; generation and database loading are intentionally separate actions.

The next step is a credentialed generation run in an isolated local file,
followed by a human/source review of all seven bill classifications, committee
IDs, unmatched people, missing years, and methodology labels before loading.
