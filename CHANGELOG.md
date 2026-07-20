## 0.8.0 (2026-07-20)

### Feat

- raw adapter results, fail-fast config errors, configure(), builtin-only get_tools (#90)
- adopt native async SDK calls and remove global thread pools (#89)

## 0.7.0 (2026-07-19)

### Feat

- **tools**: add transport seam, typed search backend, result truncation, status-code errors (#87)

### Fix

- **chat**: read citations from fragments with legacy fallback (#83)
- **core**: ctx-aware as_*_tool, registry collision warnings, retry unit fix (#84)

## 0.6.1 (2026-07-19)

### Fix

- **read_document**: support renamed retrieve kwarg across glean-api-client versions (#81)

## 0.6.0 (2026-07-19)

### Fix

- **crewai**: pass args_schema to BaseTool so the LLM sees real parameters (#73)
- **adk**: expose real typed signatures so declarations and invocation work (#77)
- **openai**: sanitize strict schemas and isolate per-tool conversion failures (#76)
- **adapters**: map anyOf/union and array item types correctly in get_field_type (#75)
- **langchain**: use StructuredTool so converted tools are invocable (#74)
- **tools**: stop closing shared Glean client on every tool call (#72)

## 0.5.0 (2026-04-07)

### Feat

- add installable skills for SDK usage and tool building (#70)
- search API alignment, chat tool, deprecation path, get_tools, async support, import docs (#66)
- injectable GleanContext replaces hidden api_client() global (#62) (#65)
- **deps**: add [all] extra combining all framework adapters (CHK-001) (#27)

### Fix

- correct web search tool name from 'Web Browser' to 'Gemini Web Search' (#71)
- resolve remaining P2 eval items (CHK-111, CHK-115, CHK-118, CHK-119) (#68)
- resolve eval checklist items — dedup, dead code, error handling, imports (#67)
- namespace tool names and optimize descriptions for LLM consumption (#58)
- structured error results and consistent adapter return types (#55)
- depend on langchain-core instead of langchain to support LangGraph 1.x (#54)
- Regenerate lockfile
- align publish workflow tag trigger with commitizen tag format (#39)
- use is not None checks in read_document validation (#37)
- export Registry from top-level package (#36)
- remove pydantic BaseModel from adapters public API (#35)
- preserve float values in retry backoff config (CHK-002)
- **release**: correct broken version_files path in .cz.toml (CHK-006) (#31)

## 0.4.0 (2026-03-05)

### Feat

- support GLEAN_SERVER_URL with GLEAN_INSTANCE fallback (#26)
- **api**: Add retry configuration to API client with environment variable controls (#15)
- **dev**: adopt mise with full task parity and Node 22; move dev docs to CONTRIBUTING; README links to CONTRIBUTING (#12)

### Fix

- **adapters**: correct install hints to use glean-agent-toolkit extras

### Refactor

- rename glean_search to search across code, tests, docs, and snippets (#19)

## 0.3.0 (2025-07-21)

### Feat

- Add enhanced parameter schemas with Field metadata support

### Fix

- Adds newline to .cz.toml
- Fixes type errors during task:lint

## 0.2.0 (2025-06-05)

### Feat

- Implements Agent Builder tools as defaults
