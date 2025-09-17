#!/usr/bin/env python3
"""
Local CI Scripts for Pure3270

This script provides easy access to the same tests that run in GitHub Actions.
It's a wrapper around run_full_ci.py with common presets.

Usage:
    python local_ci.py                  # Quick CI (like GitHub quick-ci.yml)
    python local_ci.py --full           # Full CI (like GitHub ci.yml)
    python local_ci.py --pre-commit     # Pre-commit checks only
    python local_ci.py --static         # Static analysis only
    python local_ci.py --format         # Format code with black/isort
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd):
    """Run a command and return success status."""
    try:
        result = subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def format_code():
    """Format code with black and isort."""
    print("Formatting code...")

    success = True

    # Black formatting
    try:
        subprocess.run(["black", "pure3270/", "tests/", "examples/"], check=True)
        print("✓ Black formatting applied")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ Black formatting failed or not available")
        success = False

    # Isort import sorting
    try:
        subprocess.run(["isort", "pure3270/", "tests/", "examples/"], check=True)
        print("✓ Isort import sorting applied")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ Isort import sorting failed or not available")
        success = False

    return success


def main():
    parser = argparse.ArgumentParser(description="Local CI shortcuts for Pure3270")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--full", action="store_true", help="Run full CI suite (like GitHub ci.yml)"
    )
    group.add_argument(
        "--pre-commit", action="store_true", help="Run pre-commit checks only"
    )
    group.add_argument("--static", action="store_true", help="Run static analysis only")
    group.add_argument(
        "--format", action="store_true", help="Format code with black and isort"
    )

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    full_ci_script = script_dir / "run_full_ci.py"

    if not full_ci_script.exists():
        print("Error: run_full_ci.py not found")
        sys.exit(1)

    if args.format:
        success = format_code()
        sys.exit(0 if success else 1)

    elif args.pre_commit:
        # Run only pre-commit hooks
        cmd = [
            sys.executable,
            str(full_ci_script),
            "--skip-coverage",
            "--skip-integration",
            "--skip-static",
        ]

    elif args.static:
        # Run only static analysis
        cmd = [
            sys.executable,
            str(full_ci_script),
            "--skip-hooks",
            "--skip-coverage",
            "--skip-integration",
        ]

    elif args.full:
        # Run full CI suite
        cmd = [sys.executable, str(full_ci_script)]

    else:
        # Default: Quick CI (like GitHub quick-ci.yml)
        cmd = [sys.executable, str(full_ci_script), "--skip-coverage", "--fast"]

    print(f"Running: {' '.join(cmd)}")
    success = run_command(cmd)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
