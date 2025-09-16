#!/usr/bin/env python3
"""Script to check for new Python releases and update testing matrix."""

import requests
import json
import shutil
from datetime import datetime
from typing import List, Dict, Any
import subprocess
import sys
import re

PYTHON_RELEASES_URL = "https://endoflife.date/api/python.json"

def get_latest_python_versions() -> List[Dict[str, Any]]:
    """Fetch latest Python versions from endoflife.date API."""
    try:
        response = requests.get(PYTHON_RELEASES_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Warning: Could not fetch from endoflife.date API: {e}")
        # Fallback to known recent versions
        return [
            {"v": "3.13", "eol": False},
            {"v": "3.12", "eol": False},
            {"v": "3.11", "eol": False},
            {"v": "3.10", "eol": False},
            {"v": "3.9", "eol": False},
            {"v": "3.8", "eol": False}
        ]

def get_supported_versions() -> List[str]:
    """Get currently supported Python versions from pyproject.toml."""
    try:
        with open("pyproject.toml", "r") as f:
            content = f.read()
        
        # Parse requires-python
        lines = content.splitlines()
        for line in lines:
            if "requires-python" in line:
                # Extract version range, e.g. ">=3.8"
                match = re.search(r'requires-python\s*=\s*["\']([^"\']+)["\']', line)
                if match:
                    # Simple parse for >=3.8
                    if match.group(1).startswith('>=3.8'):
                        return [f"3.{minor}" for minor in range(8, 14)]  # 3.8 to 3.13
        
        # Fallback: extract from classifiers
        for line in lines:
            if "Programming Language :: Python :: 3." in line:
                version_match = re.search(r'Python :: 3\.(\d+)', line)
                if version_match:
                    continue  # We could collect these but let's use the fallback
        
        return ["3.8", "3.9", "3.10", "3.11", "3.12", "3.13"]  # Default fallback
    except Exception as e:
        print(f"Error reading pyproject.toml: {e}")
        return ["3.8", "3.9", "3.10", "3.11", "3.12", "3.13"]  # Safe fallback

def update_ci_matrix(new_versions: List[str]) -> None:
    """Update GitHub workflow matrix with new Python versions."""
    workflow_files = [
        ".github/workflows/ci.yml",
        ".github/workflows/comprehensive-python-testing.yml",
        ".github/workflows/quick-ci.yml"
    ]
    
    for workflow_file in workflow_files:
        try:
            with open(workflow_file, "r") as f:
                content = f.read()
            
            # Find matrix and update python-version
            lines = content.splitlines()
            updated = False
            for i, line in enumerate(lines):
                if 'python-version:' in line and 'matrix' in content[:content.find(line)]:
                    # Replace with new versions - handle both quoted and unquoted formats
                    version_list = ", ".join(f'"{v}"' if "." in v else v for v in new_versions)
                    new_matrix = f"        python-version: [{version_list}]"
                    lines[i] = new_matrix
                    updated = True
                    break
            
            if updated:
                with open(workflow_file, "w") as f:
                    f.write("\n".join(lines))
                print(f"Updated {workflow_file} with versions: {new_versions}")
            else:
                print(f"Matrix not found in {workflow_file}")
        except FileNotFoundError:
            print(f"Workflow file {workflow_file} not found")
        except Exception as e:
            print(f"Error updating {workflow_file}: {e}")

def check_for_new_releases(current_versions: List[str]) -> tuple[bool, str]:
    """Check if there are new Python releases.
    
    Returns:
        tuple: (has_new_release, latest_version)
    """
    releases = get_latest_python_versions()
    latest_stable = releases[0]["v"]  # First is latest
    
    # Extract minor version numbers for comparison
    try:
        latest_minor = int(latest_stable.split('.')[1])
        current_minors = [int(v.split('.')[1]) for v in current_versions if v.startswith('3.')]
        current_max_minor = max(current_minors) if current_minors else 8
        
        if latest_minor > current_max_minor:
            print(f"New Python release detected: {latest_stable}")
            return True, latest_stable
        else:
            print(f"No new releases. Latest: {latest_stable}, Current max: 3.{current_max_minor}")
            return False, latest_stable
    except (ValueError, IndexError) as e:
        print(f"Error parsing version numbers: {e}")
        return False, latest_stable

def main():
    """Main entry point."""
    try:
        current = get_supported_versions()
        print(f"Current supported versions: {current}")
        
        has_new_release, latest_stable = check_for_new_releases(current)
        
        if has_new_release:
            # Calculate new versions to add
            latest_minor = int(latest_stable.split('.')[1])
            current_minors = [int(v.split('.')[1]) for v in current if v.startswith('3.')]
            current_max_minor = max(current_minors) if current_minors else 8
            
            # Add new versions from current max + 1 to latest
            new_minor_versions = list(range(current_max_minor + 1, latest_minor + 1))
            new_versions = current + [f"3.{minor}" for minor in new_minor_versions]
            
            print(f"Will update matrix to include: {new_versions}")
            
            # Update CI matrix
            update_ci_matrix(new_versions)
            
            # Only commit if we're in a git repository and have changes to commit
            try:
                result = subprocess.run(["git", "status", "--porcelain"], 
                                      capture_output=True, text=True, check=True)
                if result.stdout.strip():  # Has changes
                    subprocess.run(["git", "add", ".github/workflows/"], check=True)
                    subprocess.run(["git", "commit", "-m", 
                                   f"Update Python testing matrix to include {latest_stable}"], 
                                   check=True)
                    print("Changes committed successfully")
                    
                    # Only push if we have push permissions
                    try:
                        subprocess.run(["git", "push"], check=True)
                        print("Changes pushed successfully")
                    except subprocess.CalledProcessError:
                        print("Could not push changes (may need manual push)")
                else:
                    print("No changes to commit")
            except subprocess.CalledProcessError as e:
                print(f"Git operations failed: {e}")
            
            # Create issue if gh CLI is available
            if shutil.which("gh"):
                issue_title = f"Python {latest_stable} Compatibility Testing"
                issue_body = f"New Python release {latest_stable} detected. Please verify compatibility and update documentation."
                try:
                    subprocess.run(["gh", "issue", "create", "--title", issue_title, "--body", issue_body], check=True)
                    print(f"Created issue for Python {latest_stable}")
                except subprocess.CalledProcessError:
                    print("Could not create issue (may need authentication)")
            else:
                print("gh CLI not available, skipping issue creation")
        else:
            print("No new Python versions to update.")
            
    except Exception as e:
        print(f"Error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
