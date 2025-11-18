#!/usr/bin/env python3
"""
Quick smoke runner (compat wrapper).

This script simply calls into tools/quick_smoke.py runner for backward compatibility
so that `python quick_test.py` continues to work but it won't define test_* functions
that pytest would collect.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from typing import Callable

from tools.quick_smoke import run_all_smoke_tests

# Give run_all_smoke_tests a static type so mypy understands its signature
run_all_smoke_tests: Callable[[], int] = run_all_smoke_tests


def main() -> int:
    # run_all_smoke_tests isn't typed in tools/quick_smoke.py; cast to int
    return int(run_all_smoke_tests())


if __name__ == "__main__":
    sys.exit(main())
