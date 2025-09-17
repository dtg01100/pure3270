#!/usr/bin/env python3
"""
Fail CI if macro DSL is reintroduced.

This script scans the repository for forbidden terms associated with the old
macro system. If any are found in non-archive, non-generated locations, it
exits with a non-zero code.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


FORBIDDEN_PATTERNS = [
    # Function invocation or definition patterns
    r"\bdef\s+execute_macro\b",
    r"\bexecute_macro\s*\(",
    r"\bdef\s+load_macro\b",
    r"\bload_macro\s*\(",
    # Exception class reintroduction
    r"\bclass\s+MacroError\b",
]

ALLOWLIST_DIRS = {
    "archive",
    "htmlcov",
    "build",
    "dist",
    ".git",
    ".github",
    ".venv",
    "venv",
    "__pycache__",
}

ALLOWLIST_FILES_SUFFIX = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".zip",
    ".gz",
    ".tar",
    ".pdf",
    ".egg-info",
}

SCAN_EXTENSIONS = {".py"}


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & ALLOWLIST_DIRS:
        return True
    if path.suffix.lower() in ALLOWLIST_FILES_SUFFIX:
        return True
    return False


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    patterns = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_PATTERNS]
    offenders: list[Path] = []

    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if should_skip(p):
            continue
        if p.suffix.lower() not in SCAN_EXTENSIONS:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat in patterns:
            if pat.search(text):
                offenders.append(p)
                break

    if offenders:
        sys.stderr.write(
            "Macro DSL references are forbidden. Offending files:\n" +
            "\n".join(str(x) for x in sorted(set(offenders))) + "\n"
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
