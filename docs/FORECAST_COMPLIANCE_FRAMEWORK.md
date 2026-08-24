# Civic Forecasts compliance framework

Status: engineering control baseline; legal launch approval is still required where this document says **Counsel gate**.

Last reviewed: 2026-08-24

## 1. Product classification and absolute boundaries

WeThePeople Civic Forecasts is a free opinion and civic-learning feature. A participant records one private, changeable prediction about an objectively resolvable public event. WTP does not create or intermediate a financial contract and does not award value based on an outcome.

The following are prohibited in every environment:

- money, deposits, entry fees, subscriptions required to predict, or purchase consideration;
- prizes, payouts, winnings, discounts, enhanced access, or any other outcome-contingent benefit;
- purchasable, redeemable, transferable, or cash-equivalent credits, tokens, points, balances, or virtual items;
- buying, selling, trading, order books, counterparties, liquidity, cash-out, or secondary transfers;
- advertising or interface terms such as `bet`, `wager`, `stake`, `odds`, `sportsbook`, `parlay`, `payout`, or `cash out`;
- synthetic participation, test-election markets, fabricated popularity, or demo activity in real aggregates;
- paid promotion targeted by a participant's forecast or inferred political view.

This boundary follows the recurring legal distinction between a free prediction and risking something of value for something of value. The federal UIGEA definition of a bet or wager centers on staking or risking something of value for the opportunity to receive something of value. Delaware and Maryland materials likewise focus on money, consideration, and prizes. These sources are guardrails, not a 50-state legal opinion.

**Counsel gate:** any proposal involving value, incentives, paid access, tradeable instruments, or event contracts is blocked until qualified commodities, gaming, election, consumer-protection, and applicable state counsel provide written approval and the owner separately authorizes it. The CFTC describes traded event contracts as derivatives and states that public prediction markets offering swaps or futures must operate through regulated venues.

## 2. Required consumer-facing language

Every Forecast entry surface must display or link to this statement before a choice is saved:

> Civic Forecasts are free predictions for civic learning. WeThePeople does not accept bets or provide money, prizes, payouts, transferable credits, or financial contracts. Your individual choice is private. Community totals appear only after the privacy threshold is met. Forecasts are not polls, endorsements, official results, or voting advice.

Use `Predict`, `Forecast`, `Your private choice`, `Community forecast`, `Responses`, and `Resolution receipt`.

Do not use gambling or financial-market language, animated wins/losses, monetary symbols, casino imagery, countdown pressure, streak rewards, leaderboards, or dark patterns. The FTC treats interfaces that trick people into purchases or data disclosure as a consumer-protection concern.

## 3. Market taxonomy and creation rules

### 3.1 Legislation

- Subject must be an existing canonical Congress.gov bill identity.
- The question is deterministic: whether the bill becomes law before the applicable Congress ends.
- Options are `Yes` and `No` only.
- Closing time is no later than the end of the Congress and must precede resolution.
- Source must be the exact Congress.gov bill page.
- A template version is stored so later wording changes cannot silently alter an open question.

### 3.2 Elections

- Subject must be a real, current contest returned by the approved official provider or a separately reviewed official election authority.
- Test, demonstration, mock, historical, stale, or unsupported contests are forbidden.
- Candidate/option identities, office, district, election ID, date, and official source are signed into the server-issued contest reference.
- Predictions close before voting ends. WTP never describes a Forecast as a poll or result.
- The official election authority, not news projections or social media, resolves the outcome.

### 3.3 Public promises

Promise Forecasts cannot open until a reviewed Promise record contains:

- the exact promise quotation and canonical speaker/office identity;
- a primary recording, transcript, official platform, or equivalent authoritative source;
- promise date, jurisdiction, responsible level of government, and deadline;
- a measurable completion test written before predictions open;
- enumerated outcomes: `Kept`, `Partially kept`, `Not kept`, or `Unable to determine`;
- an evidence plan identifying acceptable official sources;
- reviewer identity, review timestamp, template version, and correction history.

Questions about character, intent, honesty, criminality, or other subjective/reputational judgments are forbidden. WTP forecasts performance against the quoted measurable commitment, not whether a person is generally trustworthy.

## 4. Privacy and data governance

- Individual choices are visible only to the authenticated participant and narrowly authorized operators performing security or support duties.
- Public response counts and shares remain `null` until at least five distinct real participants have valid predictions.
- The threshold is applied server-side to every representation, export, log, admin preview, and derived metric.
- Authenticated Forecast reads and all writes send `Cache-Control: no-store`; public discovery must not vary by an authenticated choice unless it is also `private, no-store` with `Vary: Authorization, Cookie`.
- Logs, analytics, error monitoring, notifications, URLs, and audit detail never contain a participant's option.
- WTP does not create political-affiliation profiles, target content/ads from choices, sell/share choices, or join choices with third-party data.
- Account export includes the user's private Forecast records. Account deletion deletes or irreversibly de-identifies the link to the individual while preserving only lawful aggregate/audit material.
- Open Forecast choices are retained while the Forecast is active. After final resolution, identifiable choices must be deleted or irreversibly de-identified under an approved retention schedule; the initial maximum is 12 months after final resolution unless a shorter operational period is established.
- The privacy notice must disclose purpose, data elements, visibility, thresholding, retention, deletion/export rights, and operator access.

California provides rights to know, delete, opt out of sale/sharing, and limit certain sensitive-data uses. WTP will honor access, correction, deletion, and opt-out requests consistently rather than attempt a state-by-state degraded experience.

## 5. Youth safety

- Forecasts are not directed to children under 13.
- The Terms prohibit Forecast participation by children under 13.
- WTP must not ask for date of birth merely to create actual knowledge without an approved age-assurance design.
- If WTP learns that an account belongs to a child under 13, Forecast collection stops and the account enters the COPPA response/deletion process.
- No gambling imagery, simulated winnings, streak pressure, or reward mechanics may be used for minors.

COPPA applies to child-directed services and general-audience services with actual knowledge that they collect personal information from a child under 13.

## 6. Election integrity

- Display `Community forecasts are not polls, endorsements, official results, or voting advice` on election Forecasts.
- Never infer registration, party, turnout, vote choice, or voting history.
- Never request an address merely to Forecast. Address-based ballot lookup remains a separate private, no-store action and must not be joined to Forecast records.
- Do not show Forecast shares beside instructions for how or where to vote in a manner that implies official status.
- Freeze predictions before the official contest closes; do not reopen after results begin.
- Use official certification/canvass sources for resolution and display source freshness.
- Corrections to candidate identity, ballot status, date, or jurisdiction lock the Forecast for review; material changes require voiding rather than silently rewriting the question.

## 7. Resolution, audit, corrections, and appeals

- Resolution requires two different authorized administrators: one proposes and one approves.
- The proposer supplies the selected outcome, official HTTPS source, evidence capture time, and a plain-language reason.
- The approver independently verifies the source and cannot be the proposer.
- Finalization is immutable. A later correction creates a superseding correction receipt; it never overwrites the original audit event.
- The public receipt includes question, frozen options, close time, final outcome or void status, reason, official source, proposed/approved timestamps, and correction history. It excludes administrator personal identifiers and all participant choices.
- Ambiguous, conflicting, unavailable, delayed, legally contested, or materially changed outcomes remain `reviewing` or become `void`; WTP must not guess.
- A visible correction/appeal channel accepts a source-backed challenge. Challenges are private until reviewed; the decision and evidence become part of the receipt.

## 8. Security and abuse controls

- Authentication, CSRF protections where applicable, idempotency, per-user uniqueness, rate limits, and authorization apply to every write.
- Market source URLs allow only HTTPS and approved authoritative host classes; arbitrary URLs cannot create or resolve a market.
- Signed election references expire and bind every material contest field.
- Administrators cannot inspect participant-level choices through ordinary product endpoints.
- Monitor coordinated account creation and automation without using political choice as an abuse feature.
- Backups containing private choices remain encrypted or access-restricted, root-owned, integrity-tested, retention-limited, and covered by deletion policy.

## 9. Accessibility and responsible design

- Choices are keyboard accessible, screen-reader labeled, and never communicated by color alone.
- Saved/private/closed/resolved states are explicit.
- Reduced motion is honored. No celebratory loss/win effects or urgency manipulation.
- Percentages identify their denominator and are never shown below threshold.
- Small-sample uncertainty and source freshness are explained in plain language.

## 10. Launch gates

All must pass before a new Forecast category reaches production:

1. Product owner approves the exact category and wording.
2. Compliance owner completes this checklist and records evidence.
3. **Counsel gate:** qualified U.S. counsel reviews the nationwide non-monetary design and a current 50-state matrix, including the operating entity's home state and states with election-wager or gambling-information provisions.
4. Privacy notice and Terms are updated before collection begins.
5. Data-flow diagram, retention schedule, deletion/export tests, threat model, and incident owner exist.
6. Market creation and resolution sources are allowlisted and tested.
7. Two-person resolution and immutable correction receipts are tested.
8. Privacy threshold, no-store behavior, logs, analytics, and account deletion are tested.
9. Accessibility, youth-safety copy, mobile layout, and dark-pattern review pass.
10. Normal CI, dependency audit, security review, backup, rollback, and live acceptance pass.

Failure of any gate blocks launch. Engineering completion is not legal approval.

## 11. Authoritative references reviewed

- [31 U.S.C. § 5362 — federal definition of bet or wager](https://www.law.cornell.edu/uscode/text/31/5362)
- [CFTC — Understanding Prediction Markets and Event Contracts](https://www.cftc.gov/LearnandProtect/PredictionMarkets)
- [CFTC — 2026 Prediction Markets advance notice](https://www.cftc.gov/LawRegulation/FederalRegister/proposedrules/2026-05105.html)
- [Delaware criminal gambling provisions](https://delcode.delaware.gov/title11/c005/sc007/index.html)
- [Delaware election provision addressing election wagers and things of value](https://www.delcode.delaware.gov/constitution/constitution-06.html)
- [Maryland Criminal Law § 12-102](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=gcr&section=12-102)
- [California Attorney General — CCPA](https://oag.ca.gov/privacy/ccpa)
- [FTC — COPPA Rule](https://www.ftc.gov/legal-library/browse/rules/childrens-online-privacy-protection-rule-coppa)
- [FTC — dark-pattern guidance](https://www.ftc.gov/news-events/news/press-releases/2022/09/ftc-report-shows-rise-sophisticated-dark-patterns-designed-trick-trap-consumers)
- [FTC — keeping privacy-enhancing-technology promises](https://www.ftc.gov/policy/advocacy-research/tech-at-ftc/2024/02/keeping-your-privacy-enhancing-technology-pet-promises)

These references are time-sensitive. Recheck them and the 50-state matrix immediately before launch and after any material product or law change.
