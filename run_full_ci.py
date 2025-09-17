#!/usr/bin/env python3
"""
Comprehensive Local CI Runner for Pure3270

This script replicates all tests that run in GitHub Actions CI workflows:
- Unit tests (pytest with markers)
- Integration tests  
- Static analysis (mypy, pylint, bandit, flake8)
- Pre-commit hooks (black, isort, etc.)
- Coverage reporting

Usage:
    python run_full_ci.py                    # Run all checks
    python run_full_ci.py --skip-hooks       # Skip pre-commit hooks
    python run_full_ci.py --skip-coverage    # Skip coverage reporting
    python run_full_ci.py --fast             # Quick mode (skip some checks)
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def print_section(title: str):
    """Print a colored section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")


def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message: str):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def run_command(cmd: List[str], description: str, cwd: Path = None, timeout: int = 300) -> Tuple[bool, str, str]:
    """
    Run a command and return success status, stdout, and stderr.
    
    Args:
        cmd: Command to run as list of strings
        description: Description for logging
        cwd: Working directory (defaults to script directory)
        timeout: Timeout in seconds
        
    Returns:
        Tuple of (success, stdout, stderr)
    """
    if cwd is None:
        cwd = Path(__file__).parent
    
    print(f"\n{Colors.YELLOW}Running: {' '.join(cmd)}{Colors.RESET}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout
        )
        
        success = result.returncode == 0
        
        if success:
            print_success(f"{description} passed")
        else:
            print_error(f"{description} failed")
            if result.stderr:
                print(f"STDERR: {result.stderr}")
            if result.stdout:
                print(f"STDOUT: {result.stdout}")
        
        return success, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        print_error(f"{description} timed out after {timeout}s")
        return False, "", "Timeout"
    except Exception as e:
        print_error(f"Error running {description}: {e}")
        return False, "", str(e)


def check_dependencies():
    """Check if required tools are installed."""
    print_section("Checking Dependencies")
    
    required_tools = [
        ("python", "Python interpreter"),
        ("pip", "Python package installer"),
    ]
    
    optional_tools = [
        ("pytest", "Testing framework"),
        ("mypy", "Type checker"),
        ("pylint", "Linter"),
        ("bandit", "Security scanner"),
        ("flake8", "Style checker"),
        ("black", "Code formatter"),
        ("isort", "Import sorter"),
        ("pre-commit", "Pre-commit hooks"),
    ]
    
    missing_required = []
    missing_optional = []
    
    for tool, desc in required_tools:
        try:
            subprocess.run([tool, "--version"], capture_output=True, check=True)
            print_success(f"{desc} available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print_error(f"{desc} missing")
            missing_required.append(tool)
    
    for tool, desc in optional_tools:
        try:
            subprocess.run([tool, "--version"], capture_output=True, check=True)
            print_success(f"{desc} available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print_warning(f"{desc} not available (some checks will be skipped)")
            missing_optional.append(tool)
    
    if missing_required:
        print_error(f"Missing required tools: {', '.join(missing_required)}")
        return False, missing_optional
    
    return True, missing_optional


def install_package():
    """Install the package in editable mode."""
    print_section("Installing Package")
    
    success, stdout, stderr = run_command(
        ["pip", "install", "-e", ".[test]"],
        "Package installation"
    )
    
    if not success:
        print_warning("Installation with [test] extras failed, trying basic install")
        success, stdout, stderr = run_command(
            ["pip", "install", "-e", "."],
            "Basic package installation"
        )
    
    return success


def run_unit_tests(fast_mode: bool = False):
    """Run unit tests with pytest."""
    print_section("Unit Tests")
    
    cmd = ["pytest", "tests/", "-v", "--tb=short", "-m", "not integration"]
    if fast_mode:
        cmd.extend(["-x"])  # Stop on first failure
    
    success, stdout, stderr = run_command(cmd, "Unit tests")
    return success


def run_integration_tests(fast_mode: bool = False):
    """Run integration tests."""
    print_section("Integration Tests")
    
    # Check if integration_test.py exists
    integration_file = Path("integration_test.py")
    if not integration_file.exists():
        print_warning("integration_test.py not found, skipping integration tests")
        return True
    
    cmd = ["pytest", "integration_test.py", "-v", "--tb=short"]
    if fast_mode:
        cmd.extend(["-x"])  # Stop on first failure
    
    success, stdout, stderr = run_command(cmd, "Integration tests")
    return success


def run_static_analysis(missing_tools: List[str]):
    """Run static analysis tools."""
    print_section("Static Analysis")
    
    all_passed = True
    
    # MyPy
    if "mypy" not in missing_tools:
        success, _, _ = run_command(
            ["mypy", "pure3270/", "--config-file=mypy.ini"],
            "MyPy type checking"
        )
        all_passed = all_passed and success
    else:
        print_warning("Skipping MyPy (not installed)")
    
    # Pylint
    if "pylint" not in missing_tools:
        success, _, _ = run_command(
            ["pylint", "pure3270/", "--rcfile=.pylintrc"],
            "Pylint analysis"
        )
        all_passed = all_passed and success
    else:
        print_warning("Skipping Pylint (not installed)")
    
    # Bandit security analysis
    if "bandit" not in missing_tools:
        success, _, _ = run_command(
            ["bandit", "-c", ".bandit", "-r", "pure3270/"],
            "Bandit security analysis"
        )
        all_passed = all_passed and success
    else:
        print_warning("Skipping Bandit (not installed)")
    
    # Flake8 style checking
    if "flake8" not in missing_tools:
        success, _, _ = run_command(
            ["flake8", "pure3270/"],
            "Flake8 style checking"
        )
        all_passed = all_passed and success
    else:
        print_warning("Skipping Flake8 (not installed)")
    
    return all_passed


def run_pre_commit_hooks(missing_tools: List[str]):
    """Run pre-commit hooks."""
    print_section("Pre-commit Hooks")
    
    if "pre-commit" in missing_tools:
        print_warning("Pre-commit not available, running individual tools")
        
        all_passed = True
        
        # Black formatting
        if "black" not in missing_tools:
            success, _, _ = run_command(
                ["black", "--check", "pure3270/"],
                "Black formatting check"
            )
            all_passed = all_passed and success
        
        # Isort import sorting
        if "isort" not in missing_tools:
            success, _, _ = run_command(
                ["isort", "--check-only", "pure3270/"],
                "Isort import sorting check"
            )
            all_passed = all_passed and success
        
        return all_passed
    
    else:
        # Run pre-commit hooks
        success, _, _ = run_command(
            ["pre-commit", "run", "--all-files"],
            "Pre-commit hooks"
        )
        return success


def run_coverage_tests(missing_tools: List[str]):
    """Run tests with coverage reporting."""
    print_section("Coverage Analysis")
    
    if "pytest" in missing_tools:
        print_warning("Pytest not available, skipping coverage")
        return True
    
    # Check if pytest-cov is available
    try:
        subprocess.run(["python", "-c", "import pytest_cov"], 
                      capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print_warning("pytest-cov not available, skipping coverage")
        return True
    
    cmd = [
        "pytest", 
        "--cov=pure3270/", 
        "--cov-report=xml",
        "--cov-report=term",
        "tests/"
    ]
    
    # Also run integration tests for coverage if they exist
    if Path("integration_test.py").exists():
        cmd.append("integration_test.py")
    
    success, stdout, stderr = run_command(cmd, "Coverage analysis")
    
    if success and "coverage.xml" in os.listdir("."):
        print_success("Coverage report generated: coverage.xml")
    
    return success


def run_quick_smoke_test():
    """Run the quick smoke test for basic validation."""
    print_section("Quick Smoke Test")
    
    if not Path("quick_test.py").exists():
        print_warning("quick_test.py not found, skipping smoke test")
        return True
    
    success, stdout, stderr = run_command(
        ["python", "quick_test.py"],
        "Quick smoke test"
    )
    return success


def main():
    """Main CI runner."""
    parser = argparse.ArgumentParser(description="Run comprehensive local CI tests")
    parser.add_argument("--skip-hooks", action="store_true", 
                       help="Skip pre-commit hooks")
    parser.add_argument("--skip-coverage", action="store_true",
                       help="Skip coverage reporting")
    parser.add_argument("--skip-static", action="store_true",
                       help="Skip static analysis")
    parser.add_argument("--skip-integration", action="store_true",
                       help="Skip integration tests")
    parser.add_argument("--fast", action="store_true",
                       help="Fast mode - skip some checks and stop on first failure")
    parser.add_argument("--install-deps", action="store_true",
                       help="Try to install missing dependencies")
    
    args = parser.parse_args()
    
    start_time = time.time()
    
    print(f"{Colors.BOLD}Pure3270 Local CI Runner{Colors.RESET}")
    print(f"Replicating GitHub Actions CI workflows locally")
    
    # Check dependencies
    deps_ok, missing_tools = check_dependencies()
    if not deps_ok:
        sys.exit(1)
    
    if args.install_deps and missing_tools:
        print_section("Installing Missing Dependencies")
        subprocess.run([sys.executable, "-m", "pip", "install"] + missing_tools)
        # Re-check after installation
        deps_ok, missing_tools = check_dependencies()
    
    # Install package
    if not install_package():
        print_error("Package installation failed")
        sys.exit(1)
    
    results = {}
    
    # Quick smoke test
    results["smoke"] = run_quick_smoke_test()
    
    # Unit tests
    results["unit"] = run_unit_tests(args.fast)
    
    # Integration tests
    if not args.skip_integration:
        results["integration"] = run_integration_tests(args.fast)
    else:
        print_warning("Skipping integration tests (--skip-integration)")
        results["integration"] = True
    
    # Static analysis
    if not args.skip_static:
        results["static"] = run_static_analysis(missing_tools)
    else:
        print_warning("Skipping static analysis (--skip-static)")
        results["static"] = True
    
    # Pre-commit hooks
    if not args.skip_hooks:
        results["hooks"] = run_pre_commit_hooks(missing_tools)
    else:
        print_warning("Skipping pre-commit hooks (--skip-hooks)")
        results["hooks"] = True
    
    # Coverage analysis
    if not args.skip_coverage:
        results["coverage"] = run_coverage_tests(missing_tools)
    else:
        print_warning("Skipping coverage analysis (--skip-coverage)")
        results["coverage"] = True
    
    # Summary
    print_section("Summary")
    
    total_time = time.time() - start_time
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, passed_status in results.items():
        if passed_status:
            print_success(f"{test_name.title()} tests")
        else:
            print_error(f"{test_name.title()} tests")
    
    print(f"\nTotal: {passed}/{total} test suites passed")
    print(f"Time: {total_time:.2f} seconds")
    
    if passed == total:
        print_success("All CI checks passed! 🎉")
        sys.exit(0)
    else:
        print_error(f"{total - passed} test suite(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()