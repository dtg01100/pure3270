#!/bin/bash
# Script to build documentation

# Exit on any error
set -e

echo "Building Pure3270 documentation..."

# Navigate to docs directory
cd "$(dirname "$0")/docs"

# Clean previous build
make clean

# Build HTML documentation
make html

echo "Documentation built successfully!"
echo "Open docs/build/html/index.html to view the documentation."
