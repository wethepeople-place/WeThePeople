# Environment inventory

Copy `.env.example` to `.env` for local development. The example contains no secrets and boots the API without external network calls.

## Clean-clone variables

| Variable | Local value | Purpose |
|---|---|---|
| `WTP_ENV` | `development` | Enables development logging and, with the next setting, local auth bypass. |
| `WTP_REQUIRE_AUTH` | `0` | Disables API-key gating only when `WTP_ENV=development`. |
| `WTP_JWT_SECRET` | replace locally | Signs local sessions; must be long, random, and secret in production. |
| `WTP_DB_URL` | `sqlite:///./wethepeople.db` | SQLAlchemy database URL. SQLite is for local development, not production social data. |
| `DISABLE_STARTUP_FETCH` | `1` | Prevents startup from fetching Federal Register data. |
| `WTP_API_URL` | `http://127.0.0.1:8006` | Vite proxy target and Expo endpoint. Use a LAN address for a physical phone. |
| `CORS_ALLOW_ORIGINS` | local frontend origins | Comma-separated allowed browser origins. |

## Optional feature groups

These are not required for a clean boot. Add only variables for the job or feature being exercised.

| Group | Variables |
|---|---|
| Official civic data | `CONGRESS_API_KEY` (legacy alias: `API_KEY_CONGRESS`), `FEC_API_KEY`, `API_KEY_GOOGLE_CIVIC`, `GOVINFO_API_KEY`, `DATAGOV_API_KEY`, `OPENSTATES_API_KEY`, `REGULATIONS_GOV_API_KEY`, `SAM_GOV_API_KEY` |
| Market/company data | `ALPHA_VANTAGE_KEY`, `FINNHUB_API_KEY`, `QUIVER_API_KEY`, `AINVEST_API_KEY`, `OPENCORPORATES_API_KEY`, `FOLLOWTHEMONEY_API_KEY`, `OPENSANCTIONS_API_KEY` |
| Other connectors | `OPENFDA_API_KEY`, `PATENTSVIEW_API_KEY`, `USPTO_API_KEY`, `FCC_API_KEY`, `SOCRATA_APP_TOKEN`, `USAJOBS_EMAIL`, `USAJOBS_API_KEY`, `SEC_USER_AGENT` |
| AI and verification | `ANTHROPIC_API_KEY`, `LLM_MODEL`, `VERITAS_BASE_URL`, `VERITAS_API_KEY` |
| Email | `RESEND_API_KEY`, `WTP_DIGEST_FROM`, `WTP_REVIEW_EMAIL`, `WTP_REVIEW_TO` |
| API access | `WTP_PRESS_API_KEY`, `WTP_ENTERPRISE_API_KEY`, `WTP_RATE_LIMIT`, `WTP_TRUSTED_PROXIES` |
| Browser builds | `VITE_API_BASE_URL`; journal only: `VITE_JOURNAL_REVIEW_MODE` |
| X/Twitter bot | `TWITTER_CONSUMER_KEY`, `TWITTER_CONSUMER_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET`, `TWITTER_BEARER_TOKEN`, `WTP_BOT_PAUSED`, `WTP_BOT_STORIES_ONLY`, `WTP_AUTO_QUOTE_DIRECT` |
| Payments | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and the `STRIPE_WTP_*_PRICE_ID` variables used in `routers/auth.py` |

Deployment and advanced pipeline controls remain documented next to their own jobs and deployment manifests. This inventory is the developer-facing contract, not permission to enable production integrations.

## Safety rules

- Never commit `.env`, access tokens, private keys, production database URLs, customer data, or database snapshots.
- Use separate development credentials with minimum scopes.
- Keep `WTP_BOT_PAUSED=1` unless a human has explicitly approved posting.
- Production must set `WTP_REQUIRE_AUTH=1`, a strong `WTP_JWT_SECRET`, explicit CORS origins, and HTTPS-safe session settings.
- Rotate a credential immediately if it appears in Git history, logs, issues, screenshots, or chat.
