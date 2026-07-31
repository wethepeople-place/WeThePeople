# Upstream relationship

This repository is the WeThePeople.place-maintained fork of [Obelus Labs LLC/WeThePeople](https://github.com/Obelus-Labs-LLC/WeThePeople). It preserves upstream Git history and the GNU Affero General Public License version 3. The fork adapts the civic evidence foundation for a social, video, discussion, solution, and citizen-action product.

## Remote layout

```bash
git remote add upstream https://github.com/Obelus-Labs-LLC/WeThePeople.git
git fetch --all --prune
```

- `origin`: `https://github.com/wethepeople-place/WeThePeople.git`
- `upstream`: `https://github.com/Obelus-Labs-LLC/WeThePeople.git`

## Reviewing an upstream sync

Never push upstream changes directly to `main`. Review them on a dedicated branch and merge through a pull request:

```bash
git switch main
git pull --ff-only origin main
git fetch upstream --prune
git switch -c upstream-sync/YYYY-MM-DD
git merge --no-ff upstream/main
```

Resolve conflicts by preserving both upstream fixes and fork-specific product, license, attribution, environment, and safety behavior. Do not resolve broad conflicts by replacing the fork wholesale with either side.

Run the gate in [`DEVELOPMENT.md`](DEVELOPMENT.md), inspect the complete change set, and open a pull request recording:

- the upstream commit range and resulting merge commit;
- user-visible, schema, dependency, deployment, and license changes;
- conflicts and why each resolution was chosen;
- verification results and known failures;
- migrations, new variables, or secret requirements.

After review, merge the pull request into the fork's `main`. Keep the upstream merge commit so future syncs retain ancestry. Rebase is appropriate for local feature branches, not for rewriting published upstream-sync history.

## Sync checklist

- Read upstream release notes, open issues, license changes, and migration notes.
- Inspect dependency and workflow changes before running code.
- Never import upstream secrets, databases, caches, generated artifacts, or deployment credentials.
- Reconcile `.env.example` and `ENVIRONMENT.md` when variable usage changes.
- Preserve upstream copyright and license notices.
- Confirm the deployed application still offers corresponding source as required by AGPL-3.0.
