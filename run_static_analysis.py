#!/usr/bin/env python3
"""
Static Analysis Runner for Pure3270

This script runs all static analysis tools (mypy, bandit, pylint) on the codebase.
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return the result."""
    print(f"\n=== {description} ===")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent)
        if result.returncode == 0:
            print("✓ Success")
            if result.stdout:
                print(result.stdout)
        else:
            print("✗ Failed")
            if result.stderr:
                print(result.stderr)
            if result.stdout:
                print(result.stdout)
        return result.returncode == 0
    except Exception as e:
        print(f"✗ Error running command: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run static analysis tools")
    parser.add_argument("--tools", nargs="+", choices=["mypy", "bandit", "pylint", "all"], 
                        default="all", help="Which tools to run")
    parser.add_argument("--parallel", action="store_true", 
                        help="Run tools in parallel")
    args = parser.parse_args()
    
    tools_to_run = args.tools if isinstance(args.tools, list) else [args.tools]
    if "all" in tools_to_run:
        tools_to_run = ["mypy", "bandit", "pylint"]
    
    # Commands for each tool
    targets = ["pure3270/", "tests/", "scripts/"]
    commands = {
        "mypy": ["python", "-m", "mypy", "--config-file", "mypy.ini"] + targets,
        "bandit": ["python", "-m", "bandit", "-c", ".bandit", "-r"] + targets,
        "pylint": ["python", "-m", "pylint", "--rcfile=.pylintrc"] + targets
    }
    
    results = {}
    
    if args.parallel:
        # Run all tools in parallel
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_tool = {
                executor.submit(run_command, commands[tool], f"Running {tool}"): tool 
                for tool in tools_to_run
            }
            
            for future in concurrent.futures.as_completed(future_to_tool):
                tool = future_to_tool[future]
                try:
                    results[tool] = future.result()
                except Exception as e:
                    print(f"Error running {tool}: {e}")
                    results[tool] = False
    else:
        # Run tools sequentially
        for tool in tools_to_run:
            if tool in commands:
                results[tool] = run_command(commands[tool], f"Running {tool}")
            else:
                print(f"Unknown tool: {tool}")
                results[tool] = False
    
    # Summary
    print("\n=== Summary ===")
    all_passed = True
    for tool, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{tool}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\nAll static analysis tools passed!")
        return 0
    else:
        print("\nSome static analysis tools failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())