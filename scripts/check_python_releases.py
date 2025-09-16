#!/usr/bin/env python3
"""Script to check for new Python releases and update testing matrix."""

import requests
import json
from datetime import datetime
from typing import List, Dict, Any
import subprocess
import sys

PYTHON_RELEASES_URL = "https://endoflife.date/api/python.json"

def get_latest_python_versions() -> List[Dict[str, Any]]:
    """Fetch latest Python versions from endoflife.date API."""
    response = requests.get(PYTHON_RELEASES_URL)
    response.raise_for_status()
    return response.json()

def get_supported_versions() -> List[str]:
    """Get currently supported Python versions from pyproject.toml."""
    with open("pyproject.toml", "r") as f:
        content = f.read()
    
    # Parse requires-python
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if "requires-python" in line:
            # Extract version range, e.g. ">=3.8"
            import re
            match = re.search(r'requires-python\s*=\s*["\']([^"\']+)["\']', line)
            if match:
                # Simple parse for >=3.8
                if match.group(1).startswith('>=3.8'):
                    return [f"3.{minor}" for minor in range(8, 13)]  # 3.8 to 3.12
    return ["3.8", "3.9", "3.10", "3.11", "3.12"]

def update_ci_matrix(new_versions: List[str]) -> None:
    """Update GitHub workflow matrix with new Python versions."""
    workflow_file = ".github/workflows/python-testing.yml"
    
    with open(workflow_file, "r") as f:
        content = f.read()
    
    # Find matrix and update python-version
    lines = content.splitlines()
    updated = False
    for i, line in enumerate(lines):
        if 'python-version:' in line:
            # Replace with new versions
            new_matrix = f"        python-version: [{', '.join(f'\"{v}\"' for v in new_versions)}]"
            lines[i] = new_matrix
            updated = True
            break
    
    if updated:
        with open(workflow_file, "w") as f:
            f.write("\n".join(lines))
        print(f"Updated {workflow_file} with versions: {new_versions}")
    else:
        print("Matrix not found or no update needed")

def check_for_new_releases(current_versions: List[str]) -> bool:
    """Check if there are new Python releases."""
    releases = get_latest_python_versions()
    latest_stable = releases[0]["v"]  # First is latest
    
    latest_minor = int(latest_stable.split('.')[-1])
    current_max_minor = max(int(v.split('.')[-1]) for v in current_versions)
    
    if latest_minor > current_max_minor:
        print(f"New Python release detected: {latest_stable}")
        return True
    return False

def main():
    """Main entry point."""
    current = get_supported_versions()
    if check_for_new_releases(current):
        # Update matrix
        new_versions = current + [f"3.{minor}" for minor in range(current_max_minor + 1, 13)]
        update_ci_matrix(new_versions)
        
        # Commit changes
        subprocess.run(["git", "add", ".github/workflows/python-testing.yml"])
        subprocess.run(["git", "commit", "-m", f"Update Python testing matrix to include {latest_stable}"])
        subprocess.run(["git", "push"])
        
        # Create issue
        issue_title = f"Python {latest_stable} Compatibility Testing"
        issue_body = f"New Python release {latest_stable} detected. Please verify compatibility and update documentation."
        # Use gh CLI if available
        if shutil.which("gh"):
            subprocess.run(["gh", "issue", "create", "--title", issue_title, "--body", issue_body])
    else:
        print("No new Python versions to update.")

if __name__ == "__main__":
    main()
