# Copilot Workflow Testing Guide

This file describes how to manually and locally validate the Copilot-related GitHub Actions workflows in this repository.

Purpose
- Verify that the Copilot workflows trigger only for relevant issues (regression + python-version) and when requested by comments.
- Avoid accidental triggers by ensuring label checks and comment checks work together.

Workflows
- `.github/workflows/copilot-regression-analysis.yml` — main analyzer for opened/reopened issues and comments
- `.github/workflows/enhanced-copilot-integration.yml` — enhanced assistance workflow for labeled issues/comments

Quick local simulation
1. We provide a small simulator that reproduces the workflows' label-check logic without contacting GitHub:

```bash
python3 scripts/simulate_copilot_label_check.py scripts/payload_issue.json issues
python3 scripts/simulate_copilot_label_check.py scripts/payload_comment.json issue_comment
```

`payload_issue.json` and `payload_comment.json` are example payloads included in `scripts/` to exercise both `issues` and `issue_comment` events.

Expected behavior
- An `issues` event with labels `regression` and `python-version` should produce `should_run: true` (workflow should proceed and post analysis comment).
- An `issue_comment` event requires the issue to have both `regression` and `python-version` labels AND also have a Copilot-specific label (`copilot-assist` or `needs-ai-analysis`) unless the workflow is being invoked by an `issues` event. If a comment contains `@copilot[analyze]` but the issue lacks a Copilot label, the workflow will not proceed (current config).

How to test live on GitHub
1. Create a test issue in the repository with title mentioning the Python version (e.g. `Python 3.11 regression: tests failing`).
2. Add labels `regression` and `python-version`.
   - If you open the issue (issues event), the workflow should run and post an automated analysis comment.
   - Alternatively, add a label `needs-ai-analysis` then post a comment containing `@copilot[analyze]` — the workflow should run for the comment.

Notes and safety
- The workflows require `GITHUB_TOKEN` permissions (standard for actions). Monitor logs for the job `label_check` to verify label detection.
- If you want comment-only triggers to work without an extra Copilot label, modify the workflows to allow `issue_comment` events where `@copilot[analyze]` alone is sufficient. Open an issue or request if you'd like that change.

Contact
- If results differ from expectations, collect the Actions run logs for the failing run and share them here; I'll inspect the `label_check` and `check_comment` steps output.
