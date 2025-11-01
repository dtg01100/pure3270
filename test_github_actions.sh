#!/bin/bash
# Script to run GitHub Actions locally with act

set -e

echo "🔧 Testing GitHub Actions locally with act..."
echo ""

# Run quick-ci workflow in dry-run mode first
echo "📋 Step 1: Dry-run to check workflow structure..."
act pull_request \
  -W .github/workflows/quick-ci.yml \
  --matrix python-version:3.12 \
  -j test \
  -P ubuntu-latest=catthehacker/ubuntu:act-latest \
  -n

echo ""
echo "✅ Dry-run completed successfully!"
echo ""
echo "To run the actual tests, execute:"
echo "  act pull_request -W .github/workflows/quick-ci.yml --matrix python-version:3.12 -j test -P ubuntu-latest=catthehacker/ubuntu:act-latest"
