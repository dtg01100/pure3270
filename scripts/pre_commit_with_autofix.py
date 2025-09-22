#!/usr/bin/env python3
"""Enhanced pre-commit wrapper that auto-fixes formatting and creates commits.

This script runs pre-commit hooks and automatically handles formatting fixes:
1. Runs all pre-commit hooks except formatting ones
2. Applies black and isort formatting to staged files
3. If formatting changes were made, creates a formatting commit
4. Re-runs all hooks to ensure everything passes

Usage:
    python scripts/pre_commit_with_autofix.py [pre-commit args]

Examples:
    python scripts/pre_commit_with_autofix.py
    python scripts/pre_commit_with_autofix.py --all-files
    python scripts/pre_commit_with_autofix.py --files file1.py file2.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Set

REPO_ROOT = Path(__file__).resolve().parent.parent


def run(
    cmd: List[str], *, check: bool = True, capture: bool = False
) -> subprocess.CompletedProcess:
    """Run a command with consistent error handling."""
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
    """Get all staged Python files."""
    try:
        proc = run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"], capture=True
        )
        files = set()
        for line in proc.stdout.splitlines():
            if line.endswith(".py"):
                files.add(Path(line))
        return files
    except subprocess.CalledProcessError:
        return set()


def has_changes_in_index() -> bool:
    """Check if there are any staged changes."""
    try:
        proc = run(["git", "diff", "--cached", "--quiet"], check=False)
        return proc.returncode != 0
    except subprocess.CalledProcessError:
        return False


def check_formatting_needed(files: Set[Path]) -> tuple[Set[Path], Set[Path]]:
    """Check which files need black or isort formatting."""
    black_needed = set()
    isort_needed = set()

    for f in files:
        # Check black
        try:
            run([sys.executable, "-m", "black", "--check", str(f)], check=True)
        except subprocess.CalledProcessError:
            black_needed.add(f)

        # Check isort
        try:
            run(
                [
                    sys.executable,
                    "-m",
                    "isort",
                    "--profile=black",
                    "--check-only",
                    str(f),
                ],
                check=True,
            )
        except subprocess.CalledProcessError:
            isort_needed.add(f)

    return black_needed, isort_needed


def apply_formatting(files: Set[Path]) -> bool:
    """Apply black and isort formatting to files. Returns True if changes were made."""
    if not files:
        return False

    file_list = [str(f) for f in files]

    # Store original content hashes to detect changes
    original_hashes = {}
    for f in files:
        if f.exists():
            original_hashes[f] = hash(f.read_bytes())

    # Apply formatting
    try:
        run([sys.executable, "-m", "black"] + file_list)
        run([sys.executable, "-m", "isort", "--profile=black"] + file_list)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Formatting failed: {e}", file=sys.stderr)
        return False

    # Check if any files actually changed
    changes_made = False
    for f in files:
        if f.exists() and f in original_hashes:
            new_hash = hash(f.read_bytes())
            if new_hash != original_hashes[f]:
                changes_made = True
                break

    return changes_made


def create_formatting_commit() -> None:
    """Create a commit with formatting changes."""
    message = "chore(format): apply black + isort auto-formatting\n\n[skip ci]"
    run(["git", "add", "-u"])  # Add all modified files
    run(["git", "commit", "--no-verify", "-m", message])
    print("✓ Created formatting commit")


def run_pre_commit_hooks(args: List[str]) -> bool:
    """Run pre-commit hooks and return success status."""
    cmd = ["pre-commit", "run"] + args
    try:
        run(cmd)
        return True
    except subprocess.CalledProcessError:
        return False


def main() -> int:
    """Main execution function."""
    # Parse arguments to pass through to pre-commit
    parser = argparse.ArgumentParser(description="Pre-commit with auto-formatting")
    parser.add_argument(
        "--all-files",
        action="store_true",
        help="Run on all files instead of just staged",
    )
    parser.add_argument("--files", nargs="*", help="Specific files to run on")
    parser.add_argument(
        "--no-auto-commit",
        action="store_true",
        help="Don't create auto-commit for formatting changes",
    )
    args, remaining_args = parser.parse_known_args()

    # Build pre-commit command arguments
    pre_commit_args = remaining_args.copy()
    if args.all_files:
        pre_commit_args.append("--all-files")
    if args.files:
        pre_commit_args.extend(["--files"] + args.files)

    print("🔍 Running pre-commit hooks...")

    # Run pre-commit hooks first
    hooks_passed = run_pre_commit_hooks(pre_commit_args)

    # If running on all files or specific files, we don't auto-commit
    if args.all_files or args.files or args.no_auto_commit:
        return 0 if hooks_passed else 1

    # For staged files, check if we need to handle formatting
    if not has_changes_in_index():
        print("ℹ️  No staged changes found")
        return 0 if hooks_passed else 1

    staged_python_files = get_staged_python_files()
    if not staged_python_files:
        print("ℹ️  No staged Python files found")
        return 0 if hooks_passed else 1

    # Check what formatting is needed
    black_needed, isort_needed = check_formatting_needed(staged_python_files)
    formatting_needed = black_needed | isort_needed

    if not formatting_needed:
        print("✓ No formatting changes needed")
        return 0 if hooks_passed else 1

    print(f"🔧 Applying formatting to {len(formatting_needed)} file(s)...")

    # Apply formatting
    changes_made = apply_formatting(formatting_needed)

    if changes_made:
        # Create formatting commit
        create_formatting_commit()

        # Re-run hooks to make sure everything passes now
        print("🔍 Re-running pre-commit hooks after formatting...")
        final_success = run_pre_commit_hooks(pre_commit_args)

        if final_success:
            print("✅ All pre-commit hooks passed after formatting")
            return 0
        else:
            print("❌ Some pre-commit hooks still failing after formatting")
            return 1
    else:
        print("ℹ️  No formatting changes were actually made")
        return 0 if hooks_passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n❌ Interrupted", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
