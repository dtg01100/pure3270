#!/bin/bash
# Pre-commit wrapper that automatically handles formatting
# Usage: ./pre-commit.sh [args]
# This replaces the standard "pre-commit run" command

exec python scripts/pre_commit_with_autofix.py "$@"
