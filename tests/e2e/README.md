# Live end-to-end tests

Everything else in `tests/` mocks the HTTP layer. This directory is the one
place that hits a **real Glean instance**, exercising the full stack: tool
functions, the transport seam, the `glean-api-client` SDK, real auth, and the
framework adapters' native invocation paths.

## Opt-in gate

E2E tests are **skipped** (never failed) unless *all* of the following are set:

| Variable | Purpose |
| --- | --- |
| `GLEAN_API_TOKEN` | Client API token for the target instance |
| `GLEAN_SERVER_URL` *or* `GLEAN_INSTANCE` | Which instance to hit (`GLEAN_SERVER_URL` e.g. `https://<instance>-be.glean.com`, or the bare instance name via `GLEAN_INSTANCE`) |
| `GLEAN_E2E=1` | Explicit opt-in. Required so a developer with real credentials exported in their shell cannot accidentally hit a live instance by running the normal suite. |

The gate is enforced in `tests/e2e/conftest.py`, which also registers the
`e2e` marker via `pytest_configure` (kept out of `pyproject.toml` on purpose)
and overrides the repo-wide fixture that fakes Glean credentials.

`mise run test` passes `--ignore=tests/e2e`, so the normal suite never even
collects these tests. Other tasks that collect them (e.g. `test:cov`) are
still safe: without `GLEAN_E2E=1` every test skips.

## Running locally

```bash
export GLEAN_API_TOKEN="<client-api-token>"
export GLEAN_INSTANCE="<instance>"          # or GLEAN_SERVER_URL=https://<instance>-be.glean.com

GLEAN_E2E=1 mise run test:e2e
# or directly:
GLEAN_E2E=1 uv run pytest -v tests/e2e/
```

## Skip vs. fail semantics

A red e2e run must mean a **real regression**, not per-instance configuration
drift. The built-in tools depend on server-side features and connectors (see
`docs/prerequisites.md`), so `tests/e2e/_live.py` classifies live errors:

| Outcome | Behavior |
| --- | --- |
| Gate not satisfied | SKIP with a one-line reason (missing creds or missing `GLEAN_E2E=1`) |
| `error_type=auth` (401/403) | **FAIL loudly** — bad credentials invalidate the whole run |
| `error_type=validation` / `not_found` (400/404/422) | SKIP with the server's reason — tool/feature not configured on this instance (e.g. Gmail/Outlook/web search disabled, unknown `tools/call` name) |
| `tools/call` 200 with a tool-level `error` in the body | SKIP with the server's reason |
| `error_type=rate_limit` (429, retries exhausted) | SKIP — flagged as likely QA contention (see below), not a regression |
| `error_type=api` / `timeout` (5xx, transport) | FAIL — real server/transport problem |

The deliberate-bad-token test (`test_error_paths_live.py`) inverts this: it
asserts that a real 401/403 is classified as
`error_type=auth` / `suggested_action=check_credentials`.

## Shared test instance realities

The repo secrets target `salessavvy-test`, QA's release-qualification
instance (the same one `gleanwork/connector-mcp` and `langchain-glean` test
against). Three things follow:

- **Contention / 429s**: QA runs post-deploy-validation sweeps after every
  release deploy, so expect 429s and latency spikes in contention windows.
  The suite defaults to generous built-in retry settings (`GLEAN_RETRY_*`
  envs, applied in `conftest.py`; your own values win). If retries are still
  exhausted, the test SKIPs with a message calling out contention.
- **Token revocation**: Glean-issued user tokens are revoked when the backing
  test user is signed out of all sessions (revocation cache). If CI suddenly
  fails with auth errors, the token may have been revoked — re-mint it and
  update the secret. The auth failure message calls this out.
- **Version skew**: `salessavvy-test` runs release-candidate builds. A live
  failure can therefore also mean an **upcoming-release regression** — that
  is signal, not noise, and worth reporting even if the toolkit itself is
  unchanged.

## Artifact hygiene

The suite is read-mostly. The only built-in that creates server-side
artifacts is `glean_chat` (a chat session); its message is prefixed with the
CI sentinel `gat-e2e-ci` per QA convention so test artifacts are identifiable
and sweepable. Any future test that creates artifacts must use the same
prefix in queries/titles.

## CI

`.github/workflows/e2e.yml` runs on `workflow_dispatch` and a weekly cron.
It is never triggered by pushes or PRs. If the repo secrets are not
configured, the job emits a notice and exits green (no-op) instead of
failing.

To configure the secrets:

```bash
gh secret set GLEAN_API_TOKEN --body "<client-api-token>"
gh secret set GLEAN_INSTANCE --body "salessavvy-test"
# or, instead of GLEAN_INSTANCE:
gh secret set GLEAN_SERVER_URL --body "https://<instance>-be.glean.com"
```

Use a token scoped to a low-privilege test user on a non-production instance.
