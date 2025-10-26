#!/usr/bin/env python3
"""
Wrapper to run the differential s3270 vs pure3270 comparison runner.

This script forwards CLI args to examples/differential_fuzz_compare.py
by invoking it as a subprocess. It's a lightweight helper so users can
run a single entrypoint from examples/.
"""

import argparse
import shlex
import subprocess
import sys
from typing import List


def parse_arguments() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run differential fuzz compare (wrapper)")
    p.add_argument(
        "--host", default=None, help="Host to pass to differential_fuzz_compare"
    )
    p.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to pass to differential_fuzz_compare",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed to pass to differential_fuzz_compare",
    )
    p.add_argument("--max-sequences", type=int, default=None, help="Max sequences")
    p.add_argument(
        "--max-commands", type=int, default=None, help="Max commands per sequence"
    )
    p.add_argument("--no-s3270", action="store_true", help="Skip running s3270")
    p.add_argument("--s3270-cmd", default=None, help="s3270 command to run")
    p.add_argument(
        "--per-command", action="store_true", help="Compare after each command"
    )
    p.add_argument(
        "extra", nargs="*", help="Extra args forwarded to the compare script"
    )
    return p.parse_args()


def build_cmd(args: argparse.Namespace) -> List[str]:
    # Default: execute the compare script with same Python interpreter
    cmd = [sys.executable, "examples/differential_fuzz_compare.py"]
    if args.host:
        cmd += ["--host", str(args.host)]
    if args.port:
        cmd += ["--port", str(args.port)]
    if args.seed:
        cmd += ["--seed", str(args.seed)]
    if args.max_sequences:
        cmd += ["--max-sequences", str(args.max_sequences)]
    if args.max_commands:
        cmd += ["--max-commands", str(args.max_commands)]
    if args.no_s3270:
        cmd += ["--no-s3270"]
    if args.s3270_cmd:
        cmd += ["--s3270-cmd", args.s3270_cmd]
    if args.per_command:
        cmd += ["--per-command"]
    if args.extra:
        # Forward any additional arguments as-is
        cmd += args.extra
    return cmd


def main() -> int:
    args = parse_arguments()
    cmd = build_cmd(args)
    print("Running:", " ".join(shlex.quote(c) for c in cmd))
    try:
        proc = subprocess.run(cmd, check=False)
        return proc.returncode
    except FileNotFoundError as e:
        print("Failed to run compare script:", e, file=sys.stderr)
        return 2
    except Exception as e:
        print("Error executing compare script:", e, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
