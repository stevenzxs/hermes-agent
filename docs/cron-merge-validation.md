# Cron controls merge validation

The Cron branch includes the prior auxiliary-reasoning fix. Merge target is this
fork's `main`, not upstream. Source pushes are not product delivery approval.

## Validation

- Backend focused tests: 126 passed across 12 files, including admission, finite
  manual budgets, concurrent round replay, profile scoping, repeat and timezone.
- Pinned Ruff pre-commit checks passed using the existing isolated test Python.
- The actual commit hook still needs a working PM development activation; a
  direct Ruff invocation does not replace successfully executing the hook.
- Android Flutter validation is in progress using an isolated Flutter 3.44.0
  checkout. No APK build or device installation is authorized by this merge.

## Fork publication safety

On 2026-11-20, before any main push, the following upstream workflows in
`stevenzxs/hermes-agent` were set to `disabled_manually` via the GitHub API:

- `docker.yml` (upstream image target: `nousresearch/hermes-agent`)
- `deploy-site.yml`
- `canary-release.yml`
- `stable-release.yml`
- `stable-release-publication.yml`

These are repository settings, not deletion of upstream workflow files or a
claim that all workflows are migrated. Do not re-enable them as this fork's
delivery route. Product build/release entry points remain in the independent
`stevenzxs/hermes-config` repository and require fixed source/config SHA pairing.
No product workflow was dispatched, and no delivery gate is closed by this note.
