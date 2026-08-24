# Civic Forecasts compliance audit

Audit date: 2026-08-24

Baseline: `d71ae0d09e8906b1b4676574892e90bf97babd4c`

This audit compares the existing Laws/Elections Forecast foundation with `FORECAST_COMPLIANCE_FRAMEWORK.md`. `PASS` means direct code/test evidence exists. `BLOCKER` means production expansion must not proceed until corrected. `COUNSEL` means engineering cannot supply the required legal conclusion.

| Requirement | Status | Current evidence | Required action |
|---|---|---|---|
| No money/value mechanics | PASS | Forecast models have no stake, price, balance, payout, prize, or transfer fields; contract tests prohibit them. | Preserve with schema and UI regression tests. |
| Non-gambling language | PARTIAL | Current UI says `Forecast` and discloses no money/prizes/payouts/points. | Add the full classification statement and forbidden-language regression scan. |
| Private individual choices | PARTIAL | Public counts/shares remain null below five; authenticated response returns only the current user's choice. | Add explicit no-store/private caching headers, `Vary`, log tests, export/deletion coverage, and retention implementation. |
| No synthetic participation | PASS for Forecasts | Production has one real owner prediction; demo discussion identities are separate. | Add a server-side prohibition against synthetic/demo accounts writing Forecasts. |
| Reviewed bill creation | PARTIAL | Questions/options/source are deterministic from canonical bill records, but any authenticated first prediction creates the market. | Store template version and freeze material fields; document why deterministic creation is approved. |
| Reviewed election creation | PARTIAL | Signed official contest token binds options/source/close time; provider test records are filtered upstream. | Persist source authority/freshness and lock/void on material contest change. |
| Promise Forecast contract | BLOCKER | No Promise market type, reviewed Promise record, measurable criteria, evidence plan, or neutral resolution vocabulary exists. | Design and implement reviewed Promise records before enabling Promise Forecasts. |
| Resolution receipt | BLOCKER | One admin can finalize; audit event exists, but reason is not returned publicly and there is no second reviewer/correction receipt. | Implement propose/approve separation, public receipt, immutable correction history, and private appeal intake. |
| Source allowlist | BLOCKER | Resolution accepts any HTTPS URL. | Add authoritative-source policy and allowlist validation by market type. |
| Election-integrity disclosure | BLOCKER | No explicit `not a poll/endorsement/result/voting advice` statement on every election surface. | Add required disclosure and tests. |
| Privacy notice | BLOCKER | Current policy does not disclose Forecast choices, purpose, threshold, retention, operator access, export, or deletion. | Update policy before expansion. |
| Terms / age / classification | BLOCKER | Current Terms do not describe Forecasts or prohibit under-13 participation. | Update Terms and legal revision date before expansion. |
| Retention schedule | BLOCKER | No identifiable-choice retention/de-identification job or policy exists. | Implement approved schedule and verifiable deletion. |
| Account rights | BLOCKER | Current audit has no proof Forecast choices participate in export/deletion. | Add export, deletion, and backup-retention tests. |
| Responsible design | PARTIAL | No money and privacy messages exist; accessible buttons are present. | Add uncertainty/source language and scan for casino/dark-pattern mechanics. |
| Nationwide legal review | COUNSEL | Engineering review includes federal, Delaware, Maryland, privacy, and youth sources only. | Qualified counsel must approve a current 50-state matrix before new-category launch. |

## Approved engineering sequence

1. Fix caching, disclosures, Terms/Privacy, synthetic-account rejection, and forbidden-language tests.
2. Add source policy, frozen template metadata, and public resolution receipts.
3. Add two-person resolution proposals/approvals and immutable corrections/appeals.
4. Add retention, export, deletion, and operator-access controls.
5. Design reviewed Promise records and Promise Forecasts behind a disabled production feature gate.
6. Complete counsel and product-owner gates before enabling Promise Forecasts or materially changing nationwide availability.

Do not deploy a partial expansion that leaves a `BLOCKER` open.
