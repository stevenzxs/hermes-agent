# Auxiliary reasoning wire repair

> Execution: focused TDD on the approved v0.23.1 baseline, branch
> `stevenzxs/fix-auxiliary-reasoning-wire`; no production update in this task.

## Contract

- Keep Kimi `chat_completions`, Android settings, approval policy and title generation enabled.
- The resolved OpenAI/AsyncOpenAI destination must not receive the Anthropic adapter's
  private `_reasoning_config` argument. Preserve provider-projected public reasoning controls.
- Native adapters must retain their private reasoning configuration and replay fields.
- Do not mutate caller-owned request dictionaries or conversation history.

## Steps and evidence

1. Add behavior tests in `tests/agent/test_auxiliary_reasoning_wire.py` for synchronous,
   asynchronous, streaming and native destinations, plus actual title/approval consumers
   with isolated config and fake HTTP responses (no model/network requests).
2. Run `scripts/run_tests.sh tests/agent/test_auxiliary_reasoning_wire.py -j 1` on unchanged
   production code; record the expected SDK argument rejection and downstream failure.
3. Extend `agent/auxiliary_wire.py::prepare_chat_messages` to discard only the private
   adapter argument when the final destination is an actual OpenAI SDK client.
4. Repeat the new tests and related wire, transport, thinking and approval tests using
   the canonical runner. Review `git diff --check` and request immutability.
5. Record source/config identity and exact verification results. Production image building,
   publishing and 150 deployment require the controlled configuration-repository route and
   separate authorization; local tests do not satisfy GOV-03/04/05 delivery acceptance.

## Governance / stop conditions

GOV-01: retain v0.23.1 / `3b421578588243f920886e6fe79a6faa87ea026e`.
GOV-02: product behavior/tests stay in source; no runtime data or credentials in Git.
GOV-03/04/05 and AUD-004/005/006/007 retain their existing unclosed states.
Stop if tests require unrelated changes, dependency installation is blocked, or a
production/configuration change becomes necessary. Do not repair installed runtimes to
run tests; prepare a fresh PM-owned environment outside the checkout instead.

## Verification (2026-11-19)

- PM `build_env --group dev --group test` created an isolated test environment at
  `C:/Users/ZL/AppData/Local/Temp/opencode/hermes-aux-test-env-20261119`.
- Red: canonical runner on the unchanged baseline produced 9 failed / 2 passed,
  reproducing `_reasoning_config` SDK rejection, title `None`, and approval `escalate`.
- Green: the same 11 regression cases passed after the boundary change.
- Compatibility: canonical runner, 10 files, 83 passed / 0 failed, retries disabled,
  2 workers. Files: new regression, auxiliary wire messages / transport autodetect /
  explicit base Anthropic / hooks, Kimi OpenAI base URL / Anthropic thinking / provider
  profile, smart approval reasoning / policy.
- Focused Ruff check and `git diff --check` passed.
- Configuration repository observed at `ab33f75fcba52ad3e8c5434ea91ae572d5dc088b`;
  its pre-existing messages diagnosis edit was preserved, not included in this repair.
- No product build, Actions dispatch, image publication, model request, production
  modification or server restart performed. 150 business acceptance remains pending.
- Submission tooling: PM `ensure('just', explicit=True)` installed and verified the
  lockfile's `just 1.59.0` in the isolated task runtime. No dependency pins changed.
  The recipe's automatic full-environment setup timed out while downloading ffmpeg;
  no setup process remained. Subsequent lint uses the existing PM test interpreter
  through `scripts/hermes-python`'s CI interpreter entry (`GITHUB_ACTIONS=true`,
  `HERMES_PYTHON` set, no activation sentinel). This is local execution, not Actions
  acceptance; the unchanged pre-commit hook and its pinned Ruff still run.
- Pre-submission verification: repeated the canonical 10-file suite (83 passed,
  0 failed, retries disabled, 2 workers), `just ruff` for both Python files, and
  `scripts/check --staged` (15 checks, 0 blocking / 0 advisory); all passed.
- Submit only this repair branch to `origin`; do not merge product `main`, push
  release tags, dispatch workflows or deploy. Existing push triggers select main,
  release tags or wine2e branches, not this repair branch.
