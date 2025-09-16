# TASK015: Set Up Pre-Commit Hooks

## Objective
Implement pre-commit hooks for linting, formatting, and basic checks.

## Requirements
- Hooks for black, isort, flake8, mypy, trailing-whitespace, etc.
- Run on git commit; optional for CI.

## Implementation Steps
1. Create .pre-commit-config.yaml with hooks from pre-commit/mirrors.
2. Install pre-commit and run `pre-commit install`.
3. Update .github/workflows to run pre-commit in CI.
4. Document in README.md: how to set up locally.
5. Test on existing code; auto-fix where possible.

## Success Metrics
- Hooks pass on main branch.
- Reduces CI failures due to style issues.
- Adoption in development workflow.

## Dependencies
- Static analysis configs (TASK013)
