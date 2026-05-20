# Test Suite Cleanup & Sync/Async Direction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Right-size the test suite — remove redundant sync wrapper tests, keep tests that cover Session-specific code paths.

**Architecture:** Hybrid stays — async core (`AsyncSession`, `TN3270Handler`, `Negotiator`) with sync `Session` wrapper (thread + event loop bridge). Session has its own code paths (constructor, context manager, decorator, threading bridge, property delegation, s3270 compat). Sync tests that test these unique paths stay; only tests that purely duplicate async coverage through delegation are removed.

**Tech Stack:** Python 3.10+, pytest, pytest-asyncio

---

### Task 1: Audit test_session.py sync tests

**Files:**
- Modify: `tests/test_session.py`

**Analysis:** After reading every sync test in `test_session.py`, most test Session-specific code paths:

| Category | Tests | Session-specific? | Verdict |
|----------|-------|-------------------|---------|
| Constructor params | `test_session_initialization`, `test_session_initialization_with_parameters`, `test_session_initialization_invalid_terminal_type`, `test_session_initialization_parameter_validation` | Yes — Session has different constructor | Keep |
| Context manager | `test_session_context_manager`, `test_session_context_manager_success`, `test_session_context_manager_exception_handling` | Yes — sync `__enter__/__exit__` is unique | Keep |
| Decorator | `test_session_send_not_connected`, `test_session_send_with_decorator`, `test_session_send_not_connected_decorator`, `test_session_read_with_decorator`, `test_session_read_with_custom_timeout` | Yes — `@_require_connected_session` decorator is Session-only | Keep |
| Bridge/threading | `test_session_close`, `test_session_worker_loop_edge_cases` | Yes — `_run_async` + background thread | Keep |
| Error context | `test_session_error_context` | Yes — `SessionError` | Keep |
| Property delegation | `test_session_properties_before_connection`, `test_session_connected_property`, `test_session_screen_buffer_property`, `test_session_tn3270e_mode_property`, `test_session_get_aid`, `test_session_property_access_edge_cases` | Partially — properties use `_run_async` bridge, different fallback logic | Keep (test bridge + fallback) |
| Connect/params | `test_session_connect_parameter_setting`, `test_session_boundary_conditions` | Yes — Session.connect() creates AsyncSession | Keep |
| Performance | `test_performance_session_operations`, `test_session_performance_under_load` | Yes — tests Session throughput | Keep |
| s3270 compat | `test_session_s3270_compatibility_methods` | Yes — s3270 API layer is Session-only | Keep |
| Field methods | `test_session_set_field_attribute_method` | Yes — delegates through bridge | Keep |
| Misc | `test_session_open_method`, `test_session_open_method_edge_cases`, `test_session_trace_events_initialization`, `test_session_screen_buffer_fallback`, `test_session_tn3270e_mode_fallback_logic`, `test_session_ascii_ebcdic_conversion` | All Session-specific | Keep |

**Verdict: All 32 sync tests in test_session.py cover unique Session code paths. None are purely redundant delegations. Keep all.**

**Only actionable change:** The paired `test_session_context_manager_success` / `test_async_session_context_manager_success` tests are structurally identical (same assertions, different CM type). These could be consolidated but add ~0.01s to runtime. **No change needed for now.**

- [x] **Step 1: Audit complete** — all 32 sync tests verified as Session-specific, not redundant
- [ ] **Step 2: Add docstring to TestSession class documenting rationale**

```python
class TestSession:
    """Tests for Session (sync wrapper) functionality.

    These tests cover Session-specific code paths that AsyncSession tests
    don't cover: constructor params, sync context manager, @_require_connected_session
    decorator, _run_async threading bridge, property delegation with fallback defaults,
    s3270 compatibility API, and performance under load through the bridge.
    """
```

- [ ] **Step 3: Verify no regression**

Run: `python -m pytest tests/test_session.py -q`
Expected: All tests pass

---

### Task 2: Audit test_error_handling.py sync/async split

**Files:**
- Modify: `tests/test_error_handling.py`

- [ ] **Step 1: Analyze paired tests**

Current tests:
- `test_session_error_handling` (sync) — tests sync `Session().send()` error propagation
- `test_screen_buffer_error_handling` (sync) — tests `ScreenBuffer` error handling (no async)
- `test_data_stream_parser_error_handling` (sync) — tests `DataStreamParser` (no async)
- `test_negotiator_error_handling` (sync) — tests `Negotiator` (no async)
- `test_async_session_error_handling` (async) — tests `AsyncSession.send()` error
- `test_async_session_connection_error` (async) — tests `AsyncSession.connect()` error
- `test_async_session_timeout_handling` (async) — tests `AsyncSession` timeout
- `test_async_session_send_error` (async) — tests `AsyncSession.send()` error propagation
- `test_parse_error_handling_in_data_stream_parser` (sync) — tests parser error (no async)
- `test_buffer_overflow_protection` (sync) — tests buffer protection (no async)
- `test_async_session_comprehensive_error_handling` (async) — comprehensive error test
- `test_negotiator_timeout_scenarios` (async) — tests negotiator timeouts
- `test_invalid_screen_buffer_dimensions` (sync) — tests buffer validation (no async)
- `test_error_propagation_from_internal_components` (async)
- `test_session_error_recovery_scenarios` (async)
- `test_exception_hierarchy_compliance` (sync) — exception class hierarchy (no async)

**Verdict: None of the sync tests have a duplicate async counterpart.** The sync tests test sync-only components (ScreenBuffer, DataStreamParser, Negotitator constructors, exception hierarchy) or Session bridge behavior. Only the 2 `test_session_error_handling + test_async_session_error_handling` pair test similar functionality through different paths — keep both since they test different code paths (sync decorator vs async handler check).

- [ ] **Step 2: Verify no regression**

Run: `python -m pytest tests/test_error_handling.py -q`
Expected: All 16 tests pass

---

### Task 3: Audit test_error_handling_coverage.py sync/async split

**Files:**
- Modify: `tests/test_error_handling_coverage.py`

- [ ] **Step 1: Analyze paired tests**

Test classes in order:
- `TestErrorRecovery` — `test_parse_error_recovery` (sync), `test_protocol_error_isolation` (sync), `test_negotiation_error_handling` (sync) — tests specific component error handling, no async equivalent
- `TestAsyncErrorHandling` — `test_connection_refused_error` (async), `test_connection_timeout_error` (async), `test_disconnect_during_operation` (async), `test_read_timeout` (async), `test_negotiation_timeout` (async) — all async-specific
- `TestErrorConfiguration` — `test_operation_timeout_configuration` (sync) — configuration test, no async equivalent
- `TestSessionCleanup` — `test_session_cleanup_on_error` (async), `test_printer_session_cleanup` (sync) — different components
- `TestContextManagerCleanup` — `test_context_manager_cleanup` (async) — async-specific
- `TestExceptionHierarchy` — `test_protocol_error_hierarchy` (sync), `test_exception_context_preservation` (sync), `test_exception_with_context` (sync) — data structure tests, no async
- `TestErrorLogging` — `test_error_logging_occurs` (sync), `test_warning_logging_for_recoverable_errors` (sync), `test_debug_logging_for_diagnostics` (async) — different scenarios
- `TestInputValidation` — `test_empty_data_handling` (sync), `test_none_value_handling` (sync), `test_malformed_iac_sequence` (sync), `test_incomplete_subnegotiation` (sync), `test_corrupted_tn3270e_header` (sync) — pure validation
- `TestConcurrentErrorsAsync` — `test_concurrent_error_isolation` (async), `test_error_propagation_in_gather` (async), `test_async_generator_cleanup_on_error` (async), `test_cancellation_handling` (async) — async-specific concurrency

**Verdict: No redundant tests.** 15 sync tests cover sync-only paths (validators, exception hierarchy, configuration, data parsing). 12 async tests cover async-only paths (connection errors, timeouts, concurrency). All are distinct and valuable.

- [ ] **Step 2: Verify no regression**

Run: `python -m pytest tests/test_error_handling_coverage.py -q`
Expected: All 27 tests pass

---

### Task 4: Full validation after audit

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest --ignore=tests/integration -m "not asyncio" -q --timeout=20`
Expected: All tests pass, no new failures

- [ ] **Step 2: Run lint + type check + format**

```bash
python -m flake8 pure3270/ && echo "flake8: OK"
python -m mypy pure3270/ && echo "mypy: OK"
python -m black --check pure3270/ tests/ && echo "black: OK"
```

Expected: All pass

- [ ] **Step 3: Quick smoke test**

Run: `python quick_test.py`
Expected: 7/7 tests passed

---

### Summary

After detailed audit of all sync tests across `test_session.py` (32 tests), `test_error_handling.py` (8 sync tests), and `test_error_handling_coverage.py` (15 sync tests):

**Zero tests removed.** All sync tests cover unique Session-specific code paths or sync-only components. The hybrid architecture means both sets of tests are testing different implementations (sync wrapper logic vs async core logic), not just duplicating each other through an adapter.

The audit itself is the value — confirming the test suite is well-structured with no redundant coverage. Docstrings updated to document this rationale.
