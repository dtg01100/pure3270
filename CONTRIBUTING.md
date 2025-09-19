# Contributing to Pure3270

Thanks for your interest in contributing! Before you start, please note:

## Macro DSL Policy (Permanent)

Macro scripting/DSL was removed from Pure3270 and will not be reintroduced.

- Do not submit PRs that add or reintroduce a macro DSL, `execute_macro`, `load_macro`, or `MacroError`.
- The CI includes a guard (`tools/forbid_macros.py`) that fails if macro DSL code or references are added back.
- Discussions and issues proposing macro DSL will be closed. Focus contributions on protocol compliance, emulation fidelity, and API quality.

## How to contribute

1. Open an issue describing the bug/feature.
2. Create a feature branch from the latest `main`.
3. Add tests for your change when practical.
4. Run local CI: `./ci.sh` (or `python run_full_ci.py --fast`).
5. Ensure formatting and linting pass: `black`, `flake8`.
6. Submit a PR with a clear description and rationale.

## Code style

- Python 3.10+
- Standard library only for runtime; optional dev tools for tests/linting.
- Format with `black`; keep imports tidy (`isort`).
- Follow RFCs for TN3270/TN3270E and Telnet behavior.
