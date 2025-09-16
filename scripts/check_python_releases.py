#!/usr/bin/env python3
"""Script to check for new Python releases and update testing matrix."""

import requests
import json
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional
import subprocess
import sys
import re

# Multiple data sources for Python version information
PYTHON_DATA_SOURCES = {
    "github_api": "https://api.github.com/repos/python/cpython/tags",
    "pypi_api": "https://pypi.org/pypi/python-version-info/json", 
    "endoflife": "https://endoflife.date/api/python.json"
}

# Known stable Python versions as of 2024 (fallback data)
# This should be updated manually when new stable versions are released
FALLBACK_PYTHON_VERSIONS = [
    {"v": "3.13", "eol": False, "stable": True, "eol_date": "2029-10-31"},
    {"v": "3.12", "eol": False, "stable": True, "eol_date": "2028-10-31"},
    {"v": "3.11", "eol": False, "stable": True, "eol_date": "2027-10-31"},
    {"v": "3.10", "eol": False, "stable": True, "eol_date": "2026-10-31"},
    {"v": "3.9", "eol": False, "stable": True, "eol_date": "2025-10-31"},
    {"v": "3.8", "eol": False, "stable": True, "eol_date": "2024-10-07"}
]

def get_latest_python_versions() -> List[Dict[str, Any]]:
    """Fetch latest Python versions from multiple sources with fallbacks."""
    
    # Try endoflife.date API first (most comprehensive data)
    try:
        print("Trying endoflife.date API for Python releases...")
        response = requests.get(PYTHON_DATA_SOURCES["endoflife"], timeout=10)
        response.raise_for_status()
        eol_data = response.json()
        
        # Filter for non-EOL versions and add metadata
        active_versions = []
        for item in eol_data:
            version = item.get("cycle", "")
            eol_date = item.get("eol", "")
            latest_release = item.get("latest", version)
            
            # Check if version is still active (not end-of-life)
            is_active = True
            if eol_date and eol_date != "false":
                try:
                    from datetime import datetime
                    if isinstance(eol_date, str) and eol_date not in ["false", ""]:
                        eol_datetime = datetime.strptime(eol_date, "%Y-%m-%d")
                        is_active = eol_datetime > datetime.now()
                except:
                    pass  # If we can't parse the date, assume it's active
            
            if version.startswith("3.") and is_active:
                active_versions.append({
                    "v": version,
                    "eol": False,
                    "stable": True,
                    "latest_release": latest_release,
                    "eol_date": eol_date
                })
        
        if active_versions:
            print(f"✓ Found {len(active_versions)} active Python versions from endoflife.date")
            # Sort by version number (newest first)
            active_versions.sort(key=lambda x: tuple(map(int, x["v"].split("."))), reverse=True)
            return active_versions
    
    except Exception as e:
        print(f"endoflife.date API failed: {e}")
    
    # Try GitHub API as backup (for latest development info)
    try:
        print("Trying GitHub API for Python releases...")
        response = requests.get(PYTHON_DATA_SOURCES["github_api"], timeout=10)
        response.raise_for_status()
        github_tags = response.json()
        
        # Extract stable Python 3.x versions from GitHub tags
        stable_versions = {}
        for tag in github_tags:
            tag_name = tag.get("name", "")
            if tag_name.startswith("v3.") and not any(x in tag_name for x in ["a", "b", "rc"]):
                # Look for full version pattern like v3.12.7
                version_match = re.match(r"v(3\.\d+)\.(\d+)", tag_name)
                if version_match:
                    minor_version = version_match.group(1)  # e.g., "3.12"
                    full_version = f"{minor_version}.{version_match.group(2)}"  # e.g., "3.12.7"
                    
                    # Keep the latest patch version for each minor version
                    if minor_version not in stable_versions or full_version > stable_versions[minor_version]:
                        stable_versions[minor_version] = full_version
        
        # Convert to the expected format
        github_versions = []
        for minor_version in sorted(stable_versions.keys(), key=lambda x: tuple(map(int, x.split("."))), reverse=True):
            github_versions.append({
                "v": minor_version,
                "eol": False,
                "stable": True,
                "latest_release": stable_versions[minor_version]
            })
        
        if github_versions:
            print(f"✓ Found {len(github_versions)} stable versions from GitHub API")
            return github_versions
    
    except Exception as e:
        print(f"GitHub API failed: {e}")
    
    # Use fallback data
    print("Using fallback Python version data")
    return FALLBACK_PYTHON_VERSIONS

def get_current_python_matrix_versions() -> List[str]:
    """Extract Python versions currently used in CI matrix files."""
    workflow_files = [
        ".github/workflows/ci.yml",
        ".github/workflows/comprehensive-python-testing.yml",
        ".github/workflows/quick-ci.yml"
    ]
    
    all_versions = set()
    
    for workflow_file in workflow_files:
        try:
            with open(workflow_file, "r") as f:
                content = f.read()
            
            # Find python-version matrix entries
            lines = content.splitlines()
            for line in lines:
                if 'python-version:' in line and '[' in line and ']' in line:
                    # Extract versions from matrix like: python-version: [3.8, 3.9, "3.10", 3.11, 3.12, 3.13]
                    version_match = re.search(r'python-version:\s*\[(.*?)\]', line)
                    if version_match:
                        version_str = version_match.group(1)
                        # Extract individual versions
                        versions = re.findall(r'["\']?(\d+\.\d+)["\']?', version_str)
                        all_versions.update(versions)
        except FileNotFoundError:
            print(f"Workflow file {workflow_file} not found")
        except Exception as e:
            print(f"Error reading {workflow_file}: {e}")
    
    # Convert to sorted list
    version_list = sorted(list(all_versions), key=lambda x: tuple(map(int, x.split("."))))
    print(f"Current CI matrix versions: {version_list}")
    return version_list

def detect_system_python_versions() -> List[str]:
    """Detect Python versions available on the system."""
    detected_versions = []
    
    # Try common Python version commands
    for minor in range(6, 20):  # Python 3.6 to 3.19
        version_str = f"3.{minor}"
        try:
            # Try to run python3.X --version
            result = subprocess.run([f"python{version_str}", "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and version_str in result.stdout:
                detected_versions.append(version_str)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    
    if detected_versions:
        print(f"Detected system Python versions: {detected_versions}")
    
    return detected_versions

def get_supported_versions() -> List[str]:
    """Get currently supported Python versions from multiple sources."""
    # Start with pyproject.toml
    pyproject_versions = get_pyproject_versions()
    
    # Also check current CI matrix
    ci_versions = get_current_python_matrix_versions()
    
    # Merge and deduplicate
    all_versions = set(pyproject_versions + ci_versions)
    
    # Convert to sorted list
    version_list = sorted(list(all_versions), key=lambda x: tuple(map(int, x.split("."))))
    print(f"Combined supported versions: {version_list}")
    return version_list

def get_pyproject_versions() -> List[str]:
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
        versions = []
        for line in lines:
            if "Programming Language :: Python :: 3." in line:
                version_match = re.search(r'Python :: 3\.(\d+)', line)
                if version_match:
                    versions.append(f"3.{version_match.group(1)}")
        
        if versions:
            return sorted(list(set(versions)), key=lambda x: tuple(map(int, x.split("."))))
        
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

def check_for_new_releases(current_versions: List[str]) -> tuple[bool, str, List[str]]:
    """Check if there are new Python releases.
    
    Returns:
        tuple: (has_new_release, latest_version, suggested_new_versions)
    """
    releases = get_latest_python_versions()
    if not releases:
        return False, "unknown", []
    
    latest_stable = releases[0]["v"]  # First is latest
    
    # Get all active versions from online source
    active_versions = {release["v"] for release in releases}
    
    # Check for EOL versions in current matrix
    eol_versions = []
    for version in current_versions:
        if version.startswith("3.") and version not in active_versions:
            eol_versions.append(version)
    
    if eol_versions:
        print(f"⚠️  Warning: End-of-life Python versions detected in CI matrix: {eol_versions}")
        print("    Consider removing these versions or updating to supported versions.")
    
    # Extract minor version numbers for comparison
    try:
        latest_minor = int(latest_stable.split('.')[1])
        current_minors = [int(v.split('.')[1]) for v in current_versions if v.startswith('3.')]
        current_max_minor = max(current_minors) if current_minors else 8
        
        # Check if we have new versions to add
        new_versions = []
        for release in releases:
            version = release["v"]
            if version.startswith("3.") and version not in current_versions:
                # Only add stable versions
                if not any(x in version for x in ["a", "b", "rc"]) and "." in version:
                    minor_version = int(version.split('.')[1])
                    if minor_version > current_max_minor:
                        new_versions.append(version)
        
        if new_versions:
            new_versions.sort(key=lambda x: tuple(map(int, x.split("."))))
            print(f"New Python releases detected: {new_versions}")
            return True, latest_stable, new_versions
        else:
            print(f"No new releases. Latest: {latest_stable}, Current max: 3.{current_max_minor}")
            if eol_versions:
                print(f"Note: Consider updating from EOL versions {eol_versions} to maintain security support.")
            return False, latest_stable, []
            
    except (ValueError, IndexError) as e:
        print(f"Error parsing version numbers: {e}")
        return False, latest_stable, []

def main():
    """Main entry point."""
    try:
        current = get_supported_versions()
        print(f"Current supported versions: {current}")
        
        has_new_release, latest_stable, suggested_versions = check_for_new_releases(current)
        
        if has_new_release and suggested_versions:
            # Use the suggested versions directly
            new_versions = current + suggested_versions
            # Remove duplicates and sort
            new_versions = sorted(list(set(new_versions)), key=lambda x: tuple(map(int, x.split("."))))
            
            print(f"Will update matrix to include: {new_versions}")
            
            # Update CI matrix
            update_ci_matrix(new_versions)
            
            # Only commit if we're in a git repository and have changes to commit
            try:
                result = subprocess.run(["git", "status", "--porcelain"], 
                                      capture_output=True, text=True, check=True)
                if result.stdout.strip():  # Has changes
                    subprocess.run(["git", "add", ".github/workflows/"], check=True)
                    commit_msg = f"Update Python testing matrix to include {', '.join(suggested_versions)}"
                    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
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
                issue_title = f"Python {', '.join(suggested_versions)} Compatibility Testing"
                issue_body = (f"New Python releases {', '.join(suggested_versions)} detected. "
                             f"Please verify compatibility and update documentation.")
                try:
                    subprocess.run(["gh", "issue", "create", "--title", issue_title, "--body", issue_body], check=True)
                    print(f"Created issue for Python {', '.join(suggested_versions)}")
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
