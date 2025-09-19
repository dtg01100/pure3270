# This file has been renamed to avoid module name clash with archived reference version.
#!/usr/bin/env python3
"""Script to check for new Python releases and update testing matrix."""

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# Try to import requests, fall back to graceful handling if not available
try:
    import requests
except ImportError:
    requests = None

# Multiple data sources for Python version information
PYTHON_DATA_SOURCES = {
    "github_api": "https://api.github.com/repos/python/cpython/tags",
    "endoflife": "https://endoflife.date/api/python.json",
}

# Known stable Python versions as of 2024 (fallback data)
# This should be updated manually when new stable versions are released
FALLBACK_PYTHON_VERSIONS = [
    {"v": "3.13", "eol": False, "stable": True, "eol_date": "2029-10-31"},
    {"v": "3.12", "eol": False, "stable": True, "eol_date": "2028-10-31"},
    {"v": "3.11", "eol": False, "stable": True, "eol_date": "2027-10-31"},
    {"v": "3.10", "eol": False, "stable": True, "eol_date": "2026-10-31"},
    {"v": "3.10", "eol": False, "stable": True, "eol_date": "2026-10-31"},
    {"v": "3.8", "eol": True, "stable": True, "eol_date": "2024-10-07"},
]


def get_latest_python_versions() -> List[Dict[str, Any]]:
    """Fetch latest Python versions from multiple sources with fallbacks."""

    if requests is None:
        print("requests library not available, using fallback data")
        return FALLBACK_PYTHON_VERSIONS

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
                    if isinstance(eol_date, str) and eol_date not in ["false", ""]:
                        eol_datetime = datetime.strptime(eol_date, "%Y-%m-%d")
                        is_active = eol_datetime > datetime.now()
                except:
                    pass  # If we can't parse the date, assume it's active

            if version.startswith("3.") and is_active:
                active_versions.append(
                    {
                        "v": version,
                        "eol": False,
                        "stable": True,
                        "latest_release": latest_release,
                        "eol_date": eol_date,
                    }
                )

        if active_versions:
            print(
                f"✓ Found {len(active_versions)} active Python versions from endoflife.date"
            )
            # Sort by version number (newest first)
            active_versions.sort(
                key=lambda x: tuple(map(int, x["v"].split("."))), reverse=True
            )
            return active_versions

    except Exception as e:
        print(f"endoflife.date API failed: {e}")

    # Try GitHub API as backup (for latest development info)
    if requests is not None:
        try:
            print("Trying GitHub API for Python releases...")
            response = requests.get(PYTHON_DATA_SOURCES["github_api"], timeout=10)
            response.raise_for_status()
            github_tags = response.json()

            # Extract stable Python 3.x versions from GitHub tags
            stable_versions = {}
            for tag in github_tags:
                tag_name = tag.get("name", "")
                if tag_name.startswith("v3.") and not any(
                    x in tag_name for x in ["a", "b", "rc"]
                ):
                    # Look for full version pattern like v3.12.7
                    version_match = re.match(r"v(3\.\d+)\.(\d+)", tag_name)
                    if version_match:
                        minor_version = version_match.group(1)  # e.g., "3.12"
                        full_version = f"{minor_version}.{version_match.group(2)}"  # e.g., "3.12.7"

                        # Keep the latest patch version for each minor version
                        if (
                            minor_version not in stable_versions
                            or full_version > stable_versions[minor_version]
                        ):
                            stable_versions[minor_version] = full_version

            # Convert to the expected format
            github_versions = []
            for minor_version in sorted(
                stable_versions.keys(),
                key=lambda x: tuple(map(int, x.split("."))),
                reverse=True,
            ):
                github_versions.append(
                    {
                        "v": minor_version,
                        "eol": False,
                        "stable": True,
                        "latest_release": stable_versions[minor_version],
                    }
                )

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
        ".github/workflows/quick-ci.yml",
    ]

    all_versions = set()

    for workflow_file in workflow_files:
        try:
            with open(workflow_file, "r") as f:
                content = f.read()

            # Find python-version matrix entries
            lines = content.splitlines()
            for line in lines:
                if "python-version:" in line and "[" in line and "]" in line:
                    # Extract versions from matrix like: python-version: [3.8, 3.9, "3.10", 3.11, 3.12, 3.13]
                    version_match = re.search(r"python-version:\s*\[(.*?)\]", line)
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
    version_list = sorted(
        list(all_versions), key=lambda x: tuple(map(int, x.split(".")))
    )
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
            result = subprocess.run(
                [f"python{version_str}", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
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
    version_list = sorted(
        list(all_versions), key=lambda x: tuple(map(int, x.split(".")))
    )
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
                    # Simple parse for >=3.9
                    if match.group(1).startswith(">=3.10") or match.group(1).startswith(">=3.9"):
                        return [f"3.{minor}" for minor in range(10, 14)]  # 3.10 to 3.13
                    # Fallback for old >=3.8 syntax
                    elif match.group(1).startswith(">=3.8"):
                        return [
                            f"3.{minor}" for minor in range(9, 14)
                        ]  # Updated minimum

        # Fallback: extract from classifiers
        versions = []
        for line in lines:
            if "Programming Language :: Python :: 3." in line:
                version_match = re.search(r"Python :: 3\.(\d+)", line)
                if version_match:
                    versions.append(f"3.{version_match.group(1)}")

        if versions:
            return sorted(
                list(set(versions)), key=lambda x: tuple(map(int, x.split(".")))
            )

    return ["3.10", "3.11", "3.12", "3.13"]  # Default fallback
    except Exception as e:
        print(f"Error reading pyproject.toml: {e}")
    return ["3.10", "3.11", "3.12", "3.13"]  # Safe fallback


def update_ci_matrix(new_versions: List[str]) -> None:
    """Update GitHub workflow matrix with new Python versions."""
    workflow_files = [
        ".github/workflows/ci.yml",
        ".github/workflows/comprehensive-python-testing.yml",
        ".github/workflows/quick-ci.yml",
    ]

    for workflow_file in workflow_files:
        try:
            with open(workflow_file, "r") as f:
                content = f.read()

            # Find matrix and update python-version
            lines = content.splitlines()
            updated = False
            for i, line in enumerate(lines):
                if (
                    "python-version:" in line
                    and "matrix" in content[: content.find(line)]
                ):
                    # Replace with new versions - handle both quoted and unquoted formats
                    version_list = ", ".join(
                        f'"{v}"' if "." in v else v for v in new_versions
                    )
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


def check_for_new_releases(
    current_versions: List[str],
) -> tuple[bool, str, List[str], List[str]]:
    """Check if there are new Python releases and EOL versions.

    Returns:
        tuple: (has_changes, latest_version, suggested_new_versions, eol_versions)
    """
    releases = get_latest_python_versions()
    if not releases:
        return False, "unknown", [], []

    latest_stable = releases[0]["v"]  # First is latest
    # Get all active versions from online source
    active_versions = {
        release["v"] for release in releases if not release.get("eol", False)
    }

    # Check for EOL versions in current matrix
    eol_versions = []
    for version in current_versions:
        if version.startswith("3.") and version not in active_versions:
            eol_versions.append(version)

    if eol_versions:
        print(f"⚠️  EOL Python versions detected in CI matrix: {eol_versions}")
        print("    These versions should be removed to maintain security support.")

    # Extract minor version numbers for comparison
    try:
        latest_minor = int(latest_stable.split(".")[1])
        current_minors = [
            int(v.split(".")[1]) for v in current_versions if v.startswith("3.")
        ]
        current_max_minor = max(current_minors) if current_minors else 8

        # Check if we have new versions to add
        new_versions = []
        for release in releases:
            version = release["v"]
            if version.startswith("3.") and version not in current_versions:
                # Only add stable, non-EOL versions
                if (
                    not any(x in version for x in ["a", "b", "rc"])
                    and "." in version
                    and not release.get("eol", False)
                ):
                    minor_version = int(version.split(".")[1])
                    if minor_version > current_max_minor:
                        new_versions.append(version)

        has_changes = bool(new_versions or eol_versions)

        if new_versions:
            new_versions.sort(key=lambda x: tuple(map(int, x.split("."))))
            print(f"🆕 New Python releases detected: {new_versions}")

        if has_changes:
            return True, latest_stable, new_versions, eol_versions
        else:
            print(
                f"No changes needed. Latest: {latest_stable}, Current max: 3.{current_max_minor}"
            )
            return False, latest_stable, [], []

    except (ValueError, IndexError) as e:
        print(f"Error parsing version numbers: {e}")
        return False, latest_stable, [], []


def trigger_test_workflow(new_versions: List[str]) -> bool:
    """Trigger CI test workflow for new Python versions."""
    if not shutil.which("gh"):
        print("gh CLI not available, cannot trigger test workflow")
        return False

    success_count = 0
    total_workflows = 0

    # Trigger main CI workflow with all new versions
    try:
        total_workflows += 1
        versions_str = ",".join(new_versions)
        subprocess.run(
            [
                "gh",
                "workflow",
                "run",
                "ci.yml",
                "-f",
                f"python_versions={versions_str}",
                "-f",
                "test_new_versions=true",
            ],
            check=True,
        )
        print(f"✅ Triggered main CI workflow for Python versions: {new_versions}")
        success_count += 1
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to trigger main CI workflow: {e}")

    # Trigger dedicated new version testing workflow for each version
    for version in new_versions:
        try:
            total_workflows += 1
            subprocess.run(
                [
                    "gh",
                    "workflow",
                    "run",
                    "new-python-version-testing.yml",
                    "-f",
                    f"python_version={version}",
                    "-f",
                    "test_type=full",
                    "-f",
                    "create_issue=true",
                    "-f",
                    "enable_copilot_fixes=true",
                ],
                check=True,
            )
            print(f"✅ Triggered dedicated testing workflow for Python {version}")
            success_count += 1
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to trigger dedicated testing for Python {version}: {e}")

    if success_count > 0:
        print(
            f"\n🧪 Test Summary: {success_count}/{total_workflows} workflows triggered successfully"
        )
        print(f"   📊 Monitor progress in the Actions tab")
        print(f"   🤖 Copilot will automatically create fix PRs for any test failures")
        return True
    else:
        print(
            f"\n❌ No workflows triggered successfully ({success_count}/{total_workflows})"
        )
        return False


def create_eol_removal_pr(eol_versions: List[str], current_versions: List[str]) -> bool:
    """Create a Copilot PR to remove EOL Python versions from the testing matrix."""
    if not shutil.which("gh"):
        print("gh CLI not available, cannot create EOL removal PR")
        return False

    if not eol_versions:
        return False

    # Calculate the updated matrix without EOL versions
    updated_versions = [v for v in current_versions if v not in eol_versions]

    try:
        # Create comprehensive Copilot task for EOL removal
        pr_title = f"🚨 Remove EOL Python {', '.join(eol_versions)} from testing matrix"

        pr_body = f"""## Automated EOL Python Version Removal

Python versions **{', '.join(eol_versions)}** have reached End of Life and should be removed from the testing matrix for security and maintenance reasons.

### Changes Required

**Files to Update:**
- `.github/workflows/ci.yml` - Remove {', '.join(eol_versions)} from matrix
- `.github/workflows/python-release-monitor.yml` - Update if needed
- `pyproject.toml` - Update python_requires and classifiers
- `setup.py` - Update python_requires if present
- `README.md` - Update supported Python versions documentation
- Any other documentation mentioning Python {', '.join(eol_versions)} support

**Updated Matrix Should Be:**
```yaml
python-version: [{', '.join(f'"{v}"' for v in updated_versions)}]
```

**Validation Requirements:**
- All existing tests must continue to pass
- CI workflows should run successfully with updated matrix
- Documentation should be consistent across all files
- No references to EOL versions should remain

**Why This Matters:**
- 🔒 **Security**: EOL versions no longer receive security updates
- 🛠️ **Maintenance**: Reduces testing burden and CI costs
- 📦 **Dependencies**: Many packages will drop support for EOL versions
- 🎯 **Focus**: Concentrate effort on actively supported versions

**Breaking Change Notice:**
This is a breaking change for users still on Python {', '.join(eol_versions)}. Consider:
- Adding migration guidance in commit message
- Updating changelog with upgrade instructions
- Mentioning alternative Python versions to use

#github-pull-request_copilot-coding-agent"""

        # Try to create the PR using gh CLI
        result = subprocess.run(
            [
                "gh",
                "api",
                "repos/{owner}/{repo}".replace("{owner}/{repo}", "dtg01100/pure3270"),
                "--method",
                "POST",
                "--field",
                f"title={pr_title}",
                "--field",
                f"body={pr_body}",
                "--field",
                "head=copilot/remove-eol-python-" + "-".join(eol_versions),
                "--field",
                "base=main",
                "--field",
                "draft=true",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print(
                f"✅ Created Copilot PR for EOL Python {', '.join(eol_versions)} removal"
            )
            return True
        else:
            # Fallback to creating an issue if PR creation fails
            print(f"⚠️ PR creation failed, creating issue instead...")

            issue_result = subprocess.run(
                [
                    "gh",
                    "issue",
                    "create",
                    "--title",
                    f"🚨 Remove EOL Python {', '.join(eol_versions)} from testing matrix",
                    "--body",
                    pr_body,
                    "--label",
                    "copilot-task,python-compatibility,breaking-change,security",
                    "--assignee",
                    "@copilot",
                ],
                check=True,
            )

            print(
                f"✅ Created Copilot issue for EOL Python {', '.join(eol_versions)} removal"
            )
            return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create EOL removal task: {e}")
        return False


def main():
    """Main entry point."""
    try:
        current = get_supported_versions()
        print(f"Current supported versions: {current}")

        has_changes, latest_stable, suggested_versions, eol_versions = (
            check_for_new_releases(current)
        )

        # Handle new versions
        if suggested_versions:
            # Use the suggested versions directly
            new_versions = current + suggested_versions
            # Remove duplicates and sort
            new_versions = sorted(
                list(set(new_versions)), key=lambda x: tuple(map(int, x.split(".")))
            )

            print(f"Will update matrix to include: {new_versions}")

            # Update CI matrix
            update_ci_matrix(new_versions)

            # Track if we successfully made changes and triggered workflows
            changes_committed = False
            test_triggered = False

            # Only commit if we're in a git repository and have changes to commit
            try:
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if result.stdout.strip():  # Has changes
                    subprocess.run(["git", "add", ".github/workflows/"], check=True)
                    commit_msg = f"Update Python testing matrix to include {', '.join(suggested_versions)}"
                    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
                    print("Changes committed successfully")
                    changes_committed = True

                    # Only push if we have push permissions
                    try:
                        subprocess.run(["git", "push"], check=True)
                        print("Changes pushed successfully")

                        # Trigger test workflow for new Python versions
                        print(f"\n🧪 Triggering tests for new Python versions...")
                        test_triggered = trigger_test_workflow(suggested_versions)

                    except subprocess.CalledProcessError:
                        print("Could not push changes (may need manual push)")
                        test_triggered = False
                else:
                    print("No changes to commit")
                    test_triggered = False
            except subprocess.CalledProcessError as e:
                print(f"Git operations failed: {e}")
                test_triggered = False

            # Only create issue if we actually have new versions AND successfully made changes
            if suggested_versions and (changes_committed or test_triggered):
                # Set defaults
                issue_title = (
                    f"Python {', '.join(suggested_versions)} Compatibility Testing"
                )
                test_status = (
                    "✅ Automated tests triggered"
                    if test_triggered
                    else "⚠️ Manual testing required"
                )
                # Create enhanced issue if gh CLI is available
                if shutil.which("gh"):
                    workflows_info = ""
                    if test_triggered:
                        workflows_info = f"""
        **Triggered Workflows:**
        - 🔄 Main CI workflow with Python {', '.join(suggested_versions)}
        - 🧪 Dedicated compatibility testing for each version
        - 📊 Automatic issue creation for test results
        - 🤖 **Copilot integration**: Auto-fix PRs for any compatibility issues

        **Monitor Progress:**
        - Check [Actions tab]({subprocess.run(['git', 'config', '--get', 'remote.origin.url'], capture_output=True, text=True).stdout.strip().replace('.git', '')}/actions) for live test results
        - Individual compatibility issues will be created automatically
        - **Copilot will create fix PRs** for any test failures within 5-15 minutes
        """
                else:
                    workflows_info = ""
                issue_body = (
                    f"🐍 New Python releases **{', '.join(suggested_versions)}** detected and added to testing matrix.\n\n"
                    f"**Test Status:** {test_status}\n"
                    f"{workflows_info}\n"
                    f"**Actions Completed:**\n"
                    f"- ✅ Updated CI matrix to include Python {', '.join(suggested_versions)}\n"
                    f"- {'✅' if test_triggered else '❌'} Triggered automated test workflows\n"
                    f"- ✅ Created this tracking issue\n\n"
                    f"**Expected Outcomes:**\n"
                    f"- 🧪 Comprehensive test suite execution for new Python versions\n"
                    f"- 📋 Individual compatibility reports for each version\n"
                    f"- 🔍 Identification of any breaking changes or issues\n"
                    f"- 🤖 **Automatic fixes**: Copilot PRs for any compatibility issues\n\n"
                    f"**Next Steps:**\n"
                    f"- Monitor automated test results in Actions tab\n"
                    f"- Review individual compatibility issues when created\n"
                    f"- **Review Copilot fix PRs** if any test failures occur\n"
                    f"- Test and merge Copilot fixes after review\n"
                    f"- Update documentation if compatibility is confirmed\n"
                    f"- Consider announcement of new Python version support\n\n"
                    f"**Version Details:**\n"
                    f"- **Added to matrix:** {', '.join(suggested_versions)}\n"
                    f"- **Detection date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                    f"- **Automated testing:** {'Enabled' if test_triggered else 'Requires manual intervention'}"
                )
                if shutil.which("gh"):
                    try:
                        subprocess.run(
                            [
                                "gh",
                                "issue",
                                "create",
                                "--title",
                                issue_title,
                                "--body",
                                issue_body,
                                "--label",
                                "python-compatibility,enhancement",
                                "--assignee",
                                "@copilot",
                            ],
                            check=True,
                        )
                        print(
                            f"✅ Created comprehensive tracking issue for Python {', '.join(suggested_versions)}"
                        )
                    except subprocess.CalledProcessError:
                        print("❌ Could not create issue (may need authentication)")
                else:
                    print("gh CLI not available, skipping issue creation")
            else:
                print(
                    f"📋 Skipping issue creation - no changes committed for Python {', '.join(suggested_versions)}"
                )

        # Handle EOL versions
        if eol_versions:
            print(f"\n🚨 Processing EOL Python versions: {eol_versions}")

            # Create Copilot PR for automatic EOL removal
            eol_pr_created = create_eol_removal_pr(eol_versions, current)

            if eol_pr_created:
                print(
                    f"✅ Copilot will automatically create PR to remove EOL Python {', '.join(eol_versions)}"
                )
            else:
                print(
                    f"⚠️ Manual removal required for EOL Python {', '.join(eol_versions)}"
                )

            # Create tracking issue for EOL removal
            if shutil.which("gh"):
                eol_issue_title = f"🚨 Remove EOL Python {', '.join(eol_versions)} from testing matrix"
                eol_issue_body = (
                    f"⚠️ **BREAKING CHANGE**: Python {', '.join(eol_versions)} has reached End of Life\n\n"
                    f"**Security Impact:**\n"
                    f"- Python {', '.join(eol_versions)} no longer receives security updates\n"
                    f"- Using EOL versions exposes projects to security vulnerabilities\n"
                    f"- Most Python packages will drop support for EOL versions\n\n"
                    f"**Required Actions:**\n"
                    f"- ✅ Remove Python {', '.join(eol_versions)} from CI testing matrix\n"
                    f"- ✅ Update pyproject.toml python_requires constraint\n"
                    f"- ✅ Update documentation and README\n"
                    f"- ✅ Add migration guidance for users\n\n"
                    f"**Automated Process:**\n"
                    f"- {'🤖 Copilot PR created automatically' if eol_pr_created else '⚠️ Manual removal required'}\n"
                    f"- 📋 This issue tracks the removal process\n"
                    f"- 🔄 Review and merge PR after validation\n\n"
                    f"**Migration Guidance:**\n"
                    f"Users on Python {', '.join(eol_versions)} should upgrade to:\n"
                    f"- **Recommended**: Python {latest_stable} (latest stable)\n"
                    f"- **Minimum**: Python 3.9+ (still supported)\n\n"
                    f"**Timeline:**\n"
                    f"- **Detected**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                    f"- **Action**: Immediate removal recommended\n"
                    f"- **Impact**: Breaking change for users on EOL versions"
                )

                try:
                    subprocess.run(
                        [
                            "gh",
                            "issue",
                            "create",
                            "--title",
                            eol_issue_title,
                            "--body",
                            eol_issue_body,
                            "--label",
                            "breaking-change,security,python-compatibility,eol",
                            "--assignee",
                            "@copilot",
                        ],
                        check=True,
                    )
                    print(
                        f"✅ Created EOL tracking issue for Python {', '.join(eol_versions)}"
                    )
                except subprocess.CalledProcessError:
                    print("❌ Could not create EOL tracking issue")

        # Summary message
        if not suggested_versions and not eol_versions:
            print("✅ Python testing matrix is up to date - no changes needed.")
        else:
            summary_items = []
            if suggested_versions:
                summary_items.append(f"🆕 Added Python {', '.join(suggested_versions)}")
            if eol_versions:
                summary_items.append(
                    f"🚨 Removing EOL Python {', '.join(eol_versions)}"
                )
            print(f"📋 Summary: {' | '.join(summary_items)}")

    except Exception as e:
        print(f"Error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
