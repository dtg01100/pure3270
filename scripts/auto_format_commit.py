#!/usr/bin/env python3
"""Utility to automatically apply formatting to staged files and commit.

When pre-commit rejects due to black/isort checks on staged files, run:
    python scripts/auto_format_commit.py

The script will:
- Identify staged Python files needing formatting (via --check per file)
- Apply black + isort to those files only
- Restage the formatted versions
- Verify checks pass on the files
- Create formatting commit if changes made

Assumes clean working tree (no unstaged Python changes). Use --allow-mixed to override.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Set

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MESSAGE = "chore(format): apply black + isort auto-formatting\n\n[skip ci]"


def run(
    cmd: list[str], *, check: bool = True, capture: bool = False
) -> subprocess.CompletedProcess:
    kwargs = {}
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
        kwargs["text"] = True
    try:
        return subprocess.run(cmd, cwd=REPO_ROOT, check=check, **kwargs)
    except subprocess.CalledProcessError as e:
        if capture and e.stdout:
            sys.stderr.write(e.stdout)
        if capture and e.stderr:
            sys.stderr.write(e.stderr)
        raise


def get_staged_python_files() -> Set[Path]:
    proc = run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"], capture=True
    )
    files = set()
    for line in proc.stdout.splitlines():
        if line.endswith(".py"):
            files.add(Path(line))
    return files


def files_needing_black(files: Set[Path]) -> Set[Path]:
    needing = set()
    for f in files:
        try:
            run([sys.executable, "-m", "black", "--check", str(f)])
        except subprocess.CalledProcessError:
            needing.add(f)
    return needing


def files_needing_isort(files: Set[Path]) -> Set[Path]:
    needing = set()
    for f in files:
        try:
            run(
                [
                    sys.executable,
                    "-m",
                    "isort",
                    "--profile=black",
                    "--check-only",
                    str(f),
                ]
            )
        except subprocess.CalledProcessError:
            needing.add(f)
    return needing


def get_unstaged_python_files() -> Set[Path]:
    proc = run(["git", "diff", "--name-only", "--diff-filter=AM"], capture=True)
    files = set()
    for line in proc.stdout.splitlines():
        if line.endswith(".py"):
            files.add(Path(line))
    return files


def ensure_clean(allow_mixed: bool) -> None:
    if allow_mixed:
        return
    unstaged = get_unstaged_python_files()
    if unstaged:
        print(
            "ERROR: Unstaged Python changes present. Commit or stash them or use --allow-mixed.",
            file=sys.stderr,
        )
        sys.exit(1)


def apply_formatters_to_staged() -> Set[Path]:
    staged = get_staged_python_files()
    if not staged:
        print("No staged Python files found.")
        return set()

    black_needed = files_needing_black(staged)
    isort_needed = files_needing_isort(staged)

    to_format = black_needed | isort_needed
    if not to_format:
        print("No formatting changes needed for staged files.")
        return set()

    file_list = [str(f) for f in to_format]
    # Apply black
    run([sys.executable, "-m", "black"] + file_list)
    # Apply isort
    run([sys.executable, "-m", "isort", "--profile=black"] + file_list)

    # Restage
    run(["git", "add"] + file_list)

    # Verify checks pass now
    for f in to_format:
        try:
            run([sys.executable, "-m", "black", "--check", str(f)])
            run(
                [
                    sys.executable,
                    "-m",
                    "isort",
                    "--profile=black",
                    "--check-only",
                    str(f),
                ]
            )
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Verification failed for {f}: {e}", file=sys.stderr)
            sys.exit(1)

    return to_format


def create_commit(message: str) -> None:
    run(["git", "commit", "--no-verify", "-m", message])


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Apply formatting to staged Python files and commit."
    )
    p.add_argument(
        "--allow-mixed", action="store_true", help="Allow unstaged Python changes."
    )
    p.add_argument(
        "--no-commit", action="store_true", help="Format and restage but no commit."
    )
    p.add_argument("--message", "-m", help="Override commit message.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    ensure_clean(args.allow_mixed)

    formatted_files = apply_formatters_to_staged()
    if not formatted_files:
        return 0

    if args.no_commit:
        print(f"Formatted and restaged {len(formatted_files)} file(s) (no commit).")
        return 0

    message = args.message or DEFAULT_MESSAGE
    create_commit(message)
    print(f"Created formatting commit for {len(formatted_files)} file(s).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        raise SystemExit(1)
