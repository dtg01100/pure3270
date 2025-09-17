#!/bin/bash
# Makefile alternative for Pure3270 CI tasks
# Usage: ./ci.sh [command]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check if Python is available
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not found"
        exit 1
    fi
}

# Install dependencies
install() {
    print_header "Installing Dependencies"
    python3 -m pip install --upgrade pip
    python3 -m pip install -e .[test] || python3 -m pip install -e .
    print_success "Dependencies installed"
}

# Quick tests (smoke + unit)
quick() {
    print_header "Quick CI Tests"
    check_python
    python3 local_ci.py
}

# Full CI suite
full() {
    print_header "Full CI Suite"
    check_python
    python3 local_ci.py --full
}

# Format code
format() {
    print_header "Formatting Code"
    check_python
    python3 local_ci.py --format
}

# Pre-commit checks
precommit() {
    print_header "Pre-commit Checks"
    check_python
    python3 local_ci.py --pre-commit
}

# Static analysis only
static() {
    print_header "Static Analysis"
    check_python
    python3 local_ci.py --static
}

# Smoke test only
smoke() {
    print_header "Smoke Test"
    check_python
    if [ -f "quick_test.py" ]; then
        python3 quick_test.py
    else
        print_warning "quick_test.py not found"
    fi
}

# Clean build artifacts
clean() {
    print_header "Cleaning Build Artifacts"
    rm -rf build/ dist/ *.egg-info/ __pycache__/
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    rm -f .coverage coverage.xml
    print_success "Build artifacts cleaned"
}

# Setup development environment
setup() {
    print_header "Setting Up Development Environment"

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_header "Creating virtual environment"
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install dependencies
    install

    # Install pre-commit hooks if available
    if command -v pre-commit &> /dev/null; then
        print_header "Installing pre-commit hooks"
        pre-commit install
        print_success "Pre-commit hooks installed"
    else
        print_warning "pre-commit not available, skipping hook installation"
    fi

    print_success "Development environment ready"
    echo "To activate: source venv/bin/activate"
}

# Test GitHub Actions workflow locally
github_sim() {
    print_header "Simulating GitHub Actions Locally"
    check_python

    echo "Running tests for multiple Python versions..."

    # Test current Python version
    python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    print_header "Testing with Python $python_version"

    python3 run_full_ci.py

    print_success "GitHub Actions simulation complete"
}

# Run specific test file
test() {
    if [ -z "$2" ]; then
        print_error "Usage: $0 test <test_file>"
        exit 1
    fi

    print_header "Running Test: $2"
    check_python

    if [ -f "$2" ]; then
        python3 "$2"
    else
        print_error "Test file not found: $2"
        exit 1
    fi
}

# Help message
help() {
    echo "Pure3270 CI Helper Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  quick      - Run quick CI tests (default)"
    echo "  full       - Run full CI suite"
    echo "  format     - Format code with black and isort"
    echo "  precommit  - Run pre-commit checks"
    echo "  static     - Run static analysis only"
    echo "  smoke      - Run smoke test only"
    echo "  install    - Install dependencies"
    echo "  setup      - Setup development environment"
    echo "  clean      - Clean build artifacts"
    echo "  github     - Simulate GitHub Actions locally"
    echo "  test FILE  - Run specific test file"
    echo "  help       - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run quick tests"
    echo "  $0 full               # Run all tests"
    echo "  $0 format             # Format code"
    echo "  $0 test quick_test.py # Run specific test"
}

# Main script logic
case "${1:-quick}" in
    "install")
        install
        ;;
    "quick")
        quick
        ;;
    "full")
        full
        ;;
    "format")
        format
        ;;
    "precommit"|"pre-commit")
        precommit
        ;;
    "static")
        static
        ;;
    "smoke")
        smoke
        ;;
    "clean")
        clean
        ;;
    "setup")
        setup
        ;;
    "github"|"github-sim")
        github_sim
        ;;
    "test")
        test "$@"
        ;;
    "help"|"--help"|"-h")
        help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        help
        exit 1
        ;;
esac
