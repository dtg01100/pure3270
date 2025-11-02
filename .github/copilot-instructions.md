## Pure3270: AI agent quick-start (concise)

This repo is a pure-Python TN3270/TN3270E terminal emulator and drop‑in replacement for p3270. Use this as your ground truth when coding here.

### Big picture architecture (what matters)
- Public API: `pure3270.Session`, `pure3270.AsyncSession`, and native `P3270Client` (p3270‑compatible) from `__init__.py`.
- Core flow: Session → TN3270 handler → Negotiator → DataStream parser → ScreenBuffer (EBCDIC) → user methods.
- Key modules to study: `pure3270/session.py` (entry point, large), `pure3270/protocol/{negotiator.py,tn3270_handler.py,data_stream.py,utils.py,exceptions.py}`, `pure3270/emulation/{screen_buffer.py,ebcdic.py}`.
- RFC‑first rule: Implement and validate behavior per RFCs (1576, 1646/2355, 854–860, 1091). Prefer RFC conformance over legacy quirks. Use protocol constants from `protocol/utils.py`.

### Non‑negotiables and project conventions
- Macro DSL is permanently removed. Do NOT add or reference `execute_macro`, `load_macro`, `MacroError`. CI blocks this (`tools/forbid_macros.py`).
- Prefer async patterns internally; sync `Session` wraps `AsyncSession` correctly. Keep lifecycle tight (context managers) and always close sessions.
- EBCDIC handling via `emulation/ebcdic.py` only; screen content is EBCDIC internally—convert for display.
- Logging: `logging.getLogger(__name__)`; raise specific exceptions from `protocol/exceptions.py`.

### Developer workflow (fast path)
- Quick verify after any change:
  - `python quick_test.py` (primary smoke)
  - `python -m py_compile pure3270/*.py` (compile check)
  - Optional: `python examples/example_standalone.py` (may fail if TN3270 host blocked)
- Format/lint when available: `black pure3270/` then `flake8 pure3270/`. If PyPI is unreachable, note: "pip install fails due to network limitations" and rely on quick tests.
- Full local CI parity: `python run_full_ci.py` summarizes Smoke, Unit, Integration, Static, Hooks, Coverage. Keep GitHub Actions workflows under `.github/workflows/` in sync with this selection and document any intentional deltas in `CI_README.md`.

### When editing core behavior
- Touching protocol or parsing? Validate against RFCs and keep negotiation sequences exact. Favor constants from `protocol/utils.py`.
- After changing `session.py` or protocol modules, re‑run: `quick_test.py` → examples → `run_full_ci.py`.
- Public API changes require checking examples in `examples/` and top‑level exports in `__init__.py`.

### Integration and compatibility
- Native `P3270Client` mirrors `p3270.P3270Client` without an s3270 binary. Keep method semantics aligned with p3270 while remaining RFC‑compliant.
- SSL/TLS via Python `ssl` contexts. TN3270 default port 23; secure variant often 992. Handle timeouts and negotiate TN3270E correctly.

### Files you’ll reach for first
- `pure3270/session.py` – lifecycle, sync/async APIs, top‑level wiring
- `pure3270/protocol/negotiator.py` – telnet/TN3270E negotiation
- `pure3270/protocol/data_stream.py` – 3270 data stream parsing
- `pure3270/emulation/screen_buffer.py` – fields, attributes, cursor
- `.github/workflows/ci.yml` + `run_full_ci.py` – CI parity reference

### Guardrails and gotchas
- Don’t hardcode protocol values; import from `protocol/utils.py`.
- Async vs sync: don’t mix; use `AsyncSession` in async code, `Session` in sync, with context managers for cleanup.
- Network CI flakes are common; prioritize local smoke tests over live host examples.

### Try it quickly
- Create/close session:
  - `python -c "import pure3270; s=pure3270.Session(); print('ok'); s.close()"`
- Smoke test:
  - `python quick_test.py`
- Compile check:
  - `python -m py_compile pure3270/*.py`

For deeper docs and patterns, read `AGENTS.md`, `architecture.md`, and the modules listed above. Keep CI in sync with `run_full_ci.py`, and always prefer RFC‑compliant behavior.

### Command index
- Local smoke: `python quick_test.py`
- Compile check: `python -m py_compile pure3270/*.py`
- Full local CI summary: `python run_full_ci.py`
- Format/lint: `black pure3270/` then `flake8 pure3270/`
- CI parity notes: see `CI_README.md`
