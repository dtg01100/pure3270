# Test Suite Cleanup & Sync/Async Direction Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this spec task-by-task.

**Goal:** Right-size the test suite by removing redundant sync Session wrapper tests while keeping the hybrid sync/async architecture.

**Architecture:** The project stays hybrid — async core (`AsyncSession`, `TN3270Handler`, `Negotiator` using `asyncio`) with a sync `Session` wrapper (thread + event loop bridge) as the primary API for p3270 drop-in compatibility. Data model components (`ScreenBuffer`, `DataStreamParser`, `Field`, emulation, trace) remain pure sync. The test suite is trimmed of redundant sync wrapper tests that duplicate async core coverage.

**Tech Stack:** Python 3.10+, pytest, pytest-asyncio

---

## Scope

### What Stays (No Change)

| Category | Test Count | Files | Rationale |
|----------|-----------|-------|-----------|
| Async core tests | ~680 | All async test files | Real coverage of async I/O, handlers, negotiators |
| Pure data structure tests | ~523 | 59 files (ScreenBuffer, DataStreamParser, Field, emulation, state machines, codecs) | Real logic, no async dependency |
| CLI tests | 4 | `test_cli.py` | Tests the sync entry point (kept) |
| Integration/hercules | ~64 | `tests/integration/` | Separate from unit tests, marked as integration |
| Mixed files (low pair count) | All remaining | `test_protocol.py`, `test_tn3270_handler.py`, other mixed files | Sync tests there test sync-only classes, not wrapper delegation |

### What Gets Trimmed

| File | Remove | Keep | Rationale |
|------|--------|------|-----------|
| `tests/test_session.py` | ~30 sync `test_session_*` tests | 3-5 bridge validation tests | The 201 async tests cover the real logic; sync tests just test `_run_async()` delegation |
| `tests/test_error_handling.py` | ~6 sync tests | 2 sync tests | Paired with async tests of same error scenarios |
| `tests/test_error_handling_coverage.py` | ~10 sync tests | 5 sync tests | Similar trim of paired coverage |

### Bridge Simplification (Separate Task)

The `Session._ensure_worker_loop()` + background thread + `asyncio.run_coroutine_threadsafe()` pattern could be simplified to `asyncio.run()` per-call. Marked as future work — not in scope for this cleanup.

---

## Detailed File Changes

### `tests/test_session.py`

**Tests to remove** (sync `test_session_*` tests that mirror async coverage):

The following test methods in `class TestSession` are redundant because they only test that `Session._run_async()` delegates to `AsyncSession` — the async logic is fully covered by `test_async_session_*` tests:

- `test_session_initialization_no_host` → covered by `test_async_session_initialization_no_host`
- `test_session_initialization_with_host` → covered by `test_async_session_initialization_with_host`
- `test_session_context_manager` → covered by `test_async_session_context_manager`
- `test_session_connect_success` → covered by `test_async_session_connect_success`
- `test_session_connect_with_port` → covered by `test_async_session_connect_with_port`
- `test_session_connect_connection_error` → covered by `test_async_session_connect_connection_error`
- `test_session_connect_negotiation_error` → covered by `test_async_session_connect_negotiation_error`
- `test_session_send_data` → covered by `test_async_session_send_data`
- `test_session_send_all_data` → covered by `test_async_session_send_all_data`
- `test_session_read` → covered by `test_async_session_read`
- `test_session_close` → covered by `test_async_session_close`
- `test_session_is_connected` → covered by `test_async_session_is_connected`
- `test_session_screen_buffer` → covered by `test_async_session_screen_buffer`
- `test_session_tn3270e_mode` → covered by `test_async_session_tn3270e_mode`
- `test_session_enter` → covered by `test_async_session_enter`
- `test_session_pf` → covered by `test_async_session_pf`
- `test_session_pa` → covered by `test_async_session_pa`
- `test_session_key` → covered by `test_async_session_key`
- `test_session_key_set_replace_mode` → covered by `test_async_session_key_set_replace_mode`
- `test_session_key_set_insert_mode` → covered by `test_async_session_key_set_insert_mode`
- `test_session_move_cursor_to_field` → covered by `test_async_session_move_cursor_to_field`
- `test_session_move_cursor_next_field` → covered by `test_async_session_move_cursor_next_field`
- `test_session_move_cursor_prev_field` → covered by `test_async_session_move_cursor_prev_field`
- `test_session_write` → covered by `test_async_session_write`
- `test_session_wait_for_field` → covered by `test_async_session_wait_for_field`
- `test_session_find_field` → covered by `test_async_session_find_field`
- `test_session_find_all_fields` → covered by `test_async_session_find_all_fields`
- `test_session_get_text` → covered by `test_async_session_get_text`
- `test_session_tab_next_field` → covered by `test_async_session_tab_next_field`
- `test_session_tab_prev_field` → covered by `test_async_session_tab_prev_field`
- `test_session_s3270_compatibility_script` → covered by `test_async_session_s3270_compatibility_script`
- `test_session_s3270_compatibility_execute` → covered by `test_async_session_s3270_compatibility_execute`
- `test_session_s3270_compatibility_query` → covered by `test_async_session_s3270_compatibility_query`
- `test_session_s3270_compatibility_expect` → covered by `test_async_session_s3270_compatibility_expect`
- `test_session_s3270_compatibility_value` → covered by `test_async_session_s3270_compatibility_value`
- `test_session_s3270_compatibility_get_last_aid` → covered by `test_async_session_s3270_compatibility_get_last_aid`

**Tests to keep** (bridge validation, testing Session threading works):

- `test_session_connect_success` (1 test showing the bridge works end-to-end)
- `test_session_close` (1 test showing cleanup works)
- `test_session_is_connected` (1 test for property delegation through the bridge)
- `test_session_screen_buffer` (1 test for property delegation through the bridge)
- `test_session_read` (1 test for data flow through the bridge)

### `tests/test_error_handling.py`

**Tests to remove** (sync tests that mirror async coverage):

- Remove sync `test_session_*` tests that have equivalent `test_async_session_*` coverage

**Tests to keep:**

- 2 sync bridge validation tests

### `tests/test_error_handling_coverage.py`

**Tests to remove** (sync tests that mirror async coverage in `TestAsyncSessionError*`):

- Remove sync `test_session_*` tests with async equivalents

**Tests to keep:**

- 5 sync bridge validation tests

---

## Verification

After cleanup:
1. `python -m pytest --ignore=tests/integration -q` — must pass with no failures
2. `python -m flake8 pure3270/` — must pass
3. `python -m mypy pure3270/` — must pass
4. `python -m black --check pure3270/ tests/` — must pass
