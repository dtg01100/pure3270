#!/bin/bash
# Validate the multi-Python devcontainer setup

set -e

echo "🔍 Validating Multi-Python Development Environment Setup..."

# Check if we're in a devcontainer
if [ ! -f /.dockerenv ]; then
    echo "⚠️  This script is designed to run inside the devcontainer"
    echo "   Current environment may not have all Python versions available"
fi

# Validate devcontainer configuration files
echo "📁 Checking configuration files..."

if [ -f .devcontainer/devcontainer.json ]; then
    echo "✅ devcontainer.json exists"
else
    echo "❌ devcontainer.json missing"
    exit 1
fi

if [ -f .devcontainer/Dockerfile ]; then
    echo "✅ Dockerfile exists"
else
    echo "❌ Dockerfile missing"
    exit 1
fi

if [ -f .devcontainer/setup-python-versions.sh ]; then
    echo "✅ setup-python-versions.sh exists"
    if [ -x .devcontainer/setup-python-versions.sh ]; then
        echo "✅ setup-python-versions.sh is executable"
    else
        echo "❌ setup-python-versions.sh is not executable"
        exit 1
    fi
else
    echo "❌ setup-python-versions.sh missing"
    exit 1
fi

if [ -f tox.ini ]; then
    echo "✅ tox.ini exists"
else
    echo "❌ tox.ini missing"
    exit 1
fi

if [ -f MULTI_PYTHON_DEVELOPMENT.md ]; then
    echo "✅ MULTI_PYTHON_DEVELOPMENT.md exists"
else
    echo "❌ MULTI_PYTHON_DEVELOPMENT.md missing"
    exit 1
fi

# Check if pyenv is available (will only work inside devcontainer)
if command -v pyenv &> /dev/null; then
    echo "✅ pyenv is available"

    # Check Python versions
    EXPECTED_VERSIONS="3.9.21 3.10.14 3.11.10 3.12.11 3.13.1"
    echo "🐍 Checking Python versions..."

    for version in $EXPECTED_VERSIONS; do
        if pyenv versions --bare | grep -q "^${version}$"; then
            echo "✅ Python $version is installed"
        else
            echo "⚠️  Python $version is not installed (expected in devcontainer)"
        fi
    done

    # Test current Python
    echo "🎯 Current Python version: $(python --version)"

    # Test convenience scripts if they exist
    if [ -f /home/vscode/bin/test-all-pythons ]; then
        echo "✅ test-all-pythons script exists"
    else
        echo "⚠️  test-all-pythons script not found (created by setup script)"
    fi

    if [ -f /home/vscode/bin/switch-python ]; then
        echo "✅ switch-python script exists"
    else
        echo "⚠️  switch-python script not found (created by setup script)"
    fi

else
    echo "⚠️  pyenv not available (expected outside devcontainer)"
fi

# Test basic package functionality
echo "📦 Testing basic package functionality..."
if python -c "import pure3270; print('✅ pure3270 imports successfully')"; then
    echo "✅ Package import test passed"
else
    echo "❌ Package import test failed"
    exit 1
fi

# Test quick smoke test
echo "🧪 Running quick smoke test..."
if python quick_test.py > /dev/null 2>&1; then
    echo "✅ Quick smoke test passed"
else
    echo "❌ Quick smoke test failed"
    exit 1
fi

echo ""
echo "🎉 Multi-Python development environment validation complete!"
echo ""
echo "📚 Next steps:"
echo "   1. Rebuild devcontainer: Ctrl+Shift+P → 'Dev Containers: Rebuild Container'"
echo "   2. Wait for setup script to complete (~5-10 minutes)"
echo "   3. Test with: test-all-pythons"
echo "   4. Read MULTI_PYTHON_DEVELOPMENT.md for detailed usage"
echo ""
echo "🔧 Manual testing inside devcontainer:"
echo "   pyenv versions                  # List all Python versions"
echo "   switch-python 3.9.21           # Switch to Python 3.9"
echo "   test-all-pythons               # Test across all versions"
echo "   run-full-ci-all-pythons        # Full CI across all versions"
