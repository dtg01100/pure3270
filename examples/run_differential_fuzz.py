#!/usr/bin/env python3
"""
Wrapper script for running differential fuzz tests with local mock TN3270 server.

This script:
1. Starts the mock TN3270 server in the background
2. Waits for it to be ready
3. Runs the differential fuzz comparison
4. Stops the server
5. Displays results

Usage:
    python examples/run_differential_fuzz.py [fuzz options]

Examples:
    # Run with defaults (5 sequences, 20 commands max)
    python examples/run_differential_fuzz.py

    # Run more sequences for thorough testing
    python examples/run_differential_fuzz.py --max-sequences 50 --max-commands 30

    # Enable per-command comparison
    python examples/run_differential_fuzz.py --per-command

    # Use a different seed
    python examples/run_differential_fuzz.py --seed 789
"""

import argparse
import asyncio
import subprocess
import sys
import time
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def wait_for_server(host: str, port: int, timeout: float = 10.0) -> bool:
    """Wait for server to be ready by attempting to connect."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=1.0
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (ConnectionRefusedError, OSError, asyncio.TimeoutError):
            await asyncio.sleep(0.2)
    return False


async def run_with_server():
    """Run the differential fuzz test with a local mock server."""
    parser = argparse.ArgumentParser(
        description="Run differential fuzz tests with local mock TN3270 server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=2324, help="Server port (default: 2324)"
    )
    parser.add_argument(
        "--seed", type=int, default=456, help="Random seed (default: 456)"
    )
    parser.add_argument(
        "--max-sequences",
        type=int,
        default=5,
        help="Max sequences to test (default: 5)",
    )
    parser.add_argument(
        "--max-commands",
        type=int,
        default=20,
        help="Max commands per sequence (default: 20)",
    )
    parser.add_argument(
        "--per-command", action="store_true", help="Compare after each command (slower)"
    )
    parser.add_argument(
        "--s3270-cmd", default=None, help="s3270 command to use (default: auto-detect)"
    )
    parser.add_argument("--no-s3270", action="store_true", help="Skip s3270 comparison")
    parser.add_argument(
        "--keep-server", action="store_true", help="Keep server running after tests"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Differential Fuzz Testing")
    print("=" * 60)
    print(f"Host: {args.host}:{args.port}")
    print(f"Sequences: {args.max_sequences}, Max commands: {args.max_commands}")
    print(f"Per-command: {args.per_command}, Seed: {args.seed}")
    print()

    # Start mock server
    print("Starting mock TN3270 server...")
    server_proc = subprocess.Popen(
        [
            sys.executable,
            "tools/mock_tn3270_server.py",
            "--host",
            args.host,
            "--port",
            str(args.port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait for server to be ready
    print(f"Waiting for server at {args.host}:{args.port}...")
    if not await wait_for_server(args.host, args.port, timeout=10.0):
        print("ERROR: Server failed to start within 10 seconds")
        server_proc.kill()
        return 1

    print("Server ready!\n")

    # Build fuzz command
    fuzz_cmd = [
        sys.executable,
        "examples/differential_fuzz_compare.py",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--seed",
        str(args.seed),
        "--max-sequences",
        str(args.max_sequences),
        "--max-commands",
        str(args.max_commands),
    ]

    if args.per_command:
        fuzz_cmd.append("--per-command")

    if args.no_s3270:
        fuzz_cmd.append("--no-s3270")
    elif args.s3270_cmd:
        fuzz_cmd.extend(["--s3270-cmd", args.s3270_cmd])

    # Run fuzz tests
    print("Running differential fuzz tests...")
    print("-" * 60)
    try:
        result = subprocess.run(fuzz_cmd, check=False)
        exit_code = result.returncode
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        exit_code = 130
    except Exception as e:
        print(f"\nERROR running fuzz tests: {e}")
        exit_code = 1

    print("-" * 60)

    # Stop server unless --keep-server
    if args.keep_server:
        print(f"\nServer still running on {args.host}:{args.port}")
        print("Press Ctrl+C to stop it")
        try:
            server_proc.wait()
        except KeyboardInterrupt:
            print("\nStopping server...")
            server_proc.terminate()
            server_proc.wait(timeout=5)
    else:
        print("\nStopping mock server...")
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_proc.kill()
            server_proc.wait()

    print("\nDone!")

    # Show results location
    if exit_code == 0:
        print("\n✓ No differences found between pure3270 and s3270")
    else:
        print("\n✗ Differences found - check reports in test_output/:")
        print("  - diff_fuzz_issues.json")
        print("  - diff_fuzz_summary.txt")
        print("  - diff_fuzz_summary.csv")

    return exit_code


def main():
    """Entry point."""
    try:
        exit_code = asyncio.run(run_with_server())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted")
        sys.exit(130)


if __name__ == "__main__":
    main()
