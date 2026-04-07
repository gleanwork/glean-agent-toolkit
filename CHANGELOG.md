## 0.4.0 (2026-03-05)

### Feat

- Add `read_document` tool for fetching full document content by URL or document ID
- Add `GLEAN_SERVER_URL` environment variable support; `GLEAN_INSTANCE` is retained as a deprecated fallback
- Add retry backoff configuration via environment variables (`GLEAN_RETRY_INITIAL`, `GLEAN_RETRY_MAX`, `GLEAN_RETRY_MULTIPLIER`, `GLEAN_RETRY_MAX_ELAPSED`)

### Changed

- Add `glean_` prefix to all tool spec names for clarity in multi-tool agent environments (`search` → `glean_search`, `employee_search` → `glean_employee_search`, etc.)

## 0.3.0 (2025-07-21)

### Feat

- Add enhanced parameter schemas with Field metadata support

### Fix

- Adds newline to .cz.toml
- Fixes type errors during task:lint

## 0.2.0 (2025-06-05)

### Feat

- Implements Agent Builder tools as defaults
