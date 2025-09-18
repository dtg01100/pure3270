#!/bin/bash
# Setup script for Pure3270 multi-Python development environment

set -e

echo "🐍 Setting up Pure3270 multi-Python development environment..."

# Initialize pyenv in current session
export PATH="/home/vscode/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# List available Python versions
echo "📋 Available Python versions:"
pyenv versions

# Install package in each Python version
PYTHON_VERSIONS="3.9.21 3.10.14 3.11.10 3.12.11 3.13.1"

for version in $PYTHON_VERSIONS; do
    echo "📦 Installing pure3270 in Python $version..."
    pyenv shell $version
    python -m pip install --upgrade pip
    python -m pip install -e .
    
    # Try to install test dependencies (may fail for newer Python versions)
    echo "🧪 Installing test dependencies for Python $version..."
    if python -m pip install -e .[test]; then
        echo "✅ Test dependencies installed for Python $version"
    else
        echo "⚠️  Some test dependencies may not be available for Python $version"
        # Install core testing tools
        python -m pip install pytest pytest-asyncio || true
    fi
done

# Set default Python version
pyenv shell 3.12.11
echo "🎯 Default Python version set to $(python --version)"

# Create convenience scripts
cat > /home/vscode/bin/test-all-pythons << 'EOF'
#!/bin/bash
# Test pure3270 across all Python versions

set -e
export PATH="/home/vscode/.pyenv/bin:$PATH"
eval "$(pyenv init -)"

PYTHON_VERSIONS="3.9.21 3.10.14 3.11.10 3.12.11 3.13.1"
FAILED_VERSIONS=()
PASSED_VERSIONS=()

echo "🧪 Running tests across all Python versions..."

for version in $PYTHON_VERSIONS; do
    echo ""
    echo "=================== Testing Python $version ==================="
    pyenv shell $version
    
    if python quick_test.py; then
        echo "✅ Python $version: PASSED"
        PASSED_VERSIONS+=($version)
    else
        echo "❌ Python $version: FAILED"
        FAILED_VERSIONS+=($version)
    fi
done

echo ""
echo "=================== SUMMARY ==================="
echo "✅ PASSED: ${PASSED_VERSIONS[*]}"
if [ ${#FAILED_VERSIONS[@]} -gt 0 ]; then
    echo "❌ FAILED: ${FAILED_VERSIONS[*]}"
    exit 1
else
    echo "🎉 All Python versions passed!"
fi
EOF

cat > /home/vscode/bin/run-full-ci-all-pythons << 'EOF'
#!/bin/bash
# Run full CI across all Python versions

set -e
export PATH="/home/vscode/.pyenv/bin:$PATH"
eval "$(pyenv init -)"

PYTHON_VERSIONS="3.9.21 3.10.14 3.11.10 3.12.11 3.13.1"
FAILED_VERSIONS=()
PASSED_VERSIONS=()

echo "🔄 Running full CI across all Python versions..."

for version in $PYTHON_VERSIONS; do
    echo ""
    echo "=================== Full CI Python $version ==================="
    pyenv shell $version
    
    if python run_full_ci.py; then
        echo "✅ Python $version: PASSED"
        PASSED_VERSIONS+=($version)
    else
        echo "❌ Python $version: FAILED"
        FAILED_VERSIONS+=($version)
    fi
done

echo ""
echo "=================== SUMMARY ==================="
echo "✅ PASSED: ${PASSED_VERSIONS[*]}"
if [ ${#FAILED_VERSIONS[@]} -gt 0 ]; then
    echo "❌ FAILED: ${FAILED_VERSIONS[*]}"
    exit 1
else
    echo "🎉 All Python versions passed!"
fi
EOF

cat > /home/vscode/bin/switch-python << 'EOF'
#!/bin/bash
# Switch to a specific Python version

if [ -z "$1" ]; then
    echo "Usage: switch-python <version>"
    echo "Available versions:"
    pyenv versions --bare
    exit 1
fi

export PATH="/home/vscode/.pyenv/bin:$PATH"
eval "$(pyenv init -)"

pyenv shell $1
echo "🐍 Switched to Python $(python --version)"
echo "💡 To make this permanent for this session: export PYENV_VERSION=$1"
EOF

# Make scripts executable
chmod +x /home/vscode/bin/*

# Add bin to PATH
echo 'export PATH="/home/vscode/bin:$PATH"' >> ~/.bashrc

echo ""
echo "🎉 Setup complete! Available commands:"
echo "  test-all-pythons          - Run quick tests across all Python versions"
echo "  run-full-ci-all-pythons   - Run full CI across all Python versions"
echo "  switch-python <version>   - Switch to a specific Python version"
echo "  pyenv versions            - List all available Python versions"
echo ""
echo "📝 Current Python version: $(python --version)"
echo "🔧 To switch versions: switch-python 3.9.21"