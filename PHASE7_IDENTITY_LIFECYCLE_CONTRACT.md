# Phase 7 identity lifecycle contract

Scope: strengthen the existing canonical identity without adding another identity provider or changing database authority.

## Keep

- Keep `users.id` as the only account identity and the existing FastAPI password/JWT/API-key system as authority.
- Keep the six deployed roles: `free`, `student`, `pro`, `newsroom`, `enterprise`, and `admin`.
- Keep public citizen contributions under stable IDs after account anonymization. Replace the public author label with an anonymous label; do not erase civic history or silently reassign authorship.
- Keep moderation and security events when required for safety, while stripping direct identifiers and free-text details that can contain personal data.

## Replace

- Replace scattered role descriptions with one exported role contract used by authorization and tests.
- Replace individually revocable refresh tokens as the only invalidation mechanism with an account `session_version` embedded in access and refresh tokens. Incrementing it invalidates every older token.
- Replace password reset that leaves other sessions active with reset that increments `session_version`.
- Replace partial privacy export/anonymization with coverage for every canonical-user table classified in `config/identity_data_inventory.json`.
- Replace internal-only privacy functions with authenticated, password-confirmed export and irreversible anonymization endpoints. The caller cannot choose another user ID.

## Defer

- Defer external identity providers, production PostgreSQL cutover, email-verification delivery, administrator suspension UI, legal-retention policy automation, HUD, and AI.
- Defer physical deletion of the canonical user row; anonymization retains it for stable foreign keys.

## Acceptance

1. Login and refresh tokens carry the current session version; stale access and refresh tokens fail after reset or anonymization.
2. Role names have one tested source of truth.
3. Export requires the current password and returns the caller's classified account/social data without credential hashes or raw tokens.
4. Anonymization requires the current password plus an exact irreversible confirmation, clears direct identity/location/preferences, disables credentials, deletes private ballots/preferences, strips private report details, anonymizes public author labels, and invalidates all sessions.
5. Focused tests cover authorization, re-authentication, session invalidation, privacy coverage, and public/private boundaries.
