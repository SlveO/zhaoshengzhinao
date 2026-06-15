# Testing

## TDD Workflow (mandatory)

1. **Write test first** — before any implementation code
2. **Present test to user** — confirm the test case covers the requirement
3. **User confirms** — proceed to implementation
4. **Implement** — write minimal code to pass the test
5. **Verify** — dispatch `test-runner` agent to run full suite
6. **Refactor** — only after green, clean up if needed

## Independent Sub-Agent for Test Writing (HARD RULE)

Implementation code and test code MUST be written by different sub-agent instances to prevent tests from being biased toward a particular implementation.

```
Workflow:
  1. Business sub-agent (e.g., backend-dev) writes implementation code
  2. A SEPARATE test-writing sub-agent reads the implementation and writes tests
  3. The test-writing sub-agent MUST NOT modify implementation code
  4. The test-writing sub-agent uses test-runner to verify tests pass
```

| Implementation by | Tests by | Run by |
|-------------------|----------|--------|
| backend-dev | backend-dev (new session, test-only) | test-runner |
| admin-spa-dev | admin-spa-dev (new session, test-only) | test-runner |
| mini-app-dev | mini-app-dev (new session, test-only) | test-runner |

Even when both agents are the same type, they MUST be launched as independent Agent calls. The test sub-agent prompt should include file paths and a summary of the implementation, but NOT the full implementation code — it must Read the files independently.

## Test Structure

```
backend/tests/
├── unit/           # Single function/class, no I/O
├── integration/    # Database, Redis, ChromaDB with test fixtures
├── e2e/            # Full API flow through FastAPI TestClient
└── benchmarks/     # Ground-truth accuracy evaluation
```

> **Note:** Frontend test infrastructure (Vitest + React Testing Library for admin-spa, uni-app tests for mini-app) is planned but not yet set up. Testing rules below apply to backend only.

## Python Testing

- Framework: pytest with `asyncio_mode=auto` (configured in `pytest.ini`)
- Run: `pytest backend/tests/`
- Coverage: `pytest backend/tests/ --cov=backend --cov-report=term-missing`

### Mock policy
- Unit tests: mock external I/O (DB, Redis, ChromaDB, LLM API calls)
- Integration tests: use real test database (dockerized PostgreSQL), mock only external LLM APIs
- E2E tests: use FastAPI `TestClient`, real test DB, mock only DeepSeek API

### Test naming (MANDATORY)
- Files: `test_<module_name>.py`
- Functions: `test_<method>_<scenario>_<expected_result>()`
- Example: `test_evidence_accumulator_3_dimensions_transitions_to_focus()`

**FORBIDDEN**: Vague names like `test_works()`, `test_1()`, `test_new()`.

## AAA Pattern (MANDATORY)

Every test MUST follow Arrange-Act-Assert with explicit comments:

```python
async def test_create_channel_saves_encrypted_webhook(async_client, test_tenant):
    # Arrange
    payload = {"name": "test", "channel_type": "wechat_group", "webhook_url": "https://..."}

    # Act
    resp = await async_client.post("/api/v1/distribution/channels", json=payload, headers={"X-Tenant": "test"})

    # Assert
    assert resp.status_code == 201
    data = resp.json()
    assert "webhook_url_masked" in data
    assert payload["webhook_url"] not in str(data)
```

**FORBIDDEN**: Mixing Arrange/Act, missing comments, scattered assertions.

## Test Isolation (MANDATORY)

- Each test must be independent; execution order must not matter
- No shared mutable state between tests (use `scope="function"` fixtures)
- DB/Redis state cleaned by `setup_db` fixture after every test
- No global variables to pass data between tests

## Fixture Factory Pattern

- Use factory fixtures, not hardcoded test data
- Fixtures should derive from production config (e.g., `tenant_config` from `SCNU_TENANT_CONFIG` via deepcopy)
- Use `pytest.mark.parametrize` for boundary conditions

```python
# Good
@pytest.fixture
def make_channel_payload():
    def _make(name="test_channel", webhook_key="abcdef12-3456-7890-abcd-ef1234567890"):
        return {
            "name": name,
            "channel_type": "wechat_group",
            "webhook_url": f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={webhook_key}"
        }
    return _make
```

## Coverage Thresholds

| Category | Dir | Target | Mock Strategy |
|----------|-----|--------|---------------|
| Unit | `tests/unit/` | Pure logic 90%+ | Mock all I/O (DB, Redis, LLM, ChromaDB) |
| Integration | `tests/integration/` | API endpoints 80%+ | Real DB, mock LLM only |
| E2E | `tests/e2e/` | Core user journeys 100% | Real env, mock DeepSeek only |
| Benchmarks | `tests/benchmarks/` | Framework 100% | Real LLM + ground truth comparison |

**New module gating**:
- Any new `backend/services/*.py` MUST have `tests/unit/test_*.py`
- Any new API endpoint MUST have `tests/integration/test_*.py`
- PRs without tests for new modules SHALL NOT be merged

## LLM-Specific Testing

Since the project depends on LLM (DeepSeek), LLM tests require special handling:

### Mock LLM Tests (unit/integration)
Verify prompt construction, response parsing, retry logic, error handling:

```python
def test_profile_analyzer_prompt_includes_all_fields():
    prompt = build_extraction_prompt(conversation_history)
    assert "province" in prompt
    assert "RIASEC" in prompt
    assert "concern_dimensions" in prompt

def test_parse_analysis_response_handles_markdown_wrapped_json():
    result = parse_analysis_response("```json\n{\"R\": 5}\n```")
    assert result["R"] == 5
```

### Real LLM Tests (benchmarks)
Use ground truth datasets:
- KB Q&A: 100+ standard Q&A pairs
- Profile extraction: 50+ conversation+annotation pairs
- Scoring: LLM-as-judge 1-5, 4+ = correct
- Target: KB accuracy >= 95%, extraction accuracy >= 95%

### Snapshot Tests (regression)
- Save LLM output snapshots for critical prompts
- After prompt changes, run snapshot tests vs baseline
- Diff > threshold = breaking change

## Boundary & Error Path Coverage (MANDATORY)

Every module MUST cover these scenarios:

| Category | Min Tests | Example |
|----------|-----------|---------|
| Happy path | 1 | Standard input -> expected output |
| Empty/missing input | 1 | Empty conversation -> empty profile |
| Oversized input | 1 | 100+ turn conversation -> correct truncation |
| Malformed input | 1 | Non-JSON LLM output -> fallback logic |
| Concurrency | 1 | 2 simultaneous SSE connections -> no state pollution |
| Tenant isolation | 1 | Tenant A cannot access Tenant B data |

## CI Quality Gates

```
CI Pipeline:
  lint (ruff + eslint)
    -> unit tests
      -> integration tests (requires PostgreSQL)
        -> accuracy benchmarks (requires DeepSeek API key)
          -> coverage report

Gates:
  - lint: 0 errors               -> block merge
  - unit tests: 100% pass        -> block merge
  - integration tests: 100% pass -> block merge
  - accuracy: < 95%              -> warning (explain in PR)
  - coverage: below threshold    -> warning
```

## Test Code Review Checklist

Before submitting tests in a PR, verify:

- [ ] Each test follows AAA pattern with comments
- [ ] Tests are independent (can run alone and pass)
- [ ] Both positive and negative cases covered
- [ ] Boundary conditions tested (empty, oversized, malformed)
- [ ] LLM calls are mocked
- [ ] Sensitive assertions use exact matching, not loose matching
- [ ] Test name follows method_scenario_expected format
- [ ] No `time.sleep()` (use `asyncio.wait_for` or polling)
- [ ] Test data derived from fixtures, not hardcoded

## Test Runner Agent

Always use the `test-runner` agent to execute tests — it filters noise and returns condensed results, protecting main context from test output bloat.
