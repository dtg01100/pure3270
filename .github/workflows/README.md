# GitHub Actions Workflows

This directory contains the GitHub Actions workflows for the Pure3270 project.

## Workflows

### 1. `ci.yml` - Pure3270 CI/CD
- **Triggers**: Push/PR to main/develop branches, manual releases
- **Purpose**: Comprehensive testing, linting, release validation, and PyPI publishing
- **Jobs**:
  - `test`: Runs tests and linting across multiple Python versions (3.8-3.13)
  - `release-validation`: Validates releases when manually created
  - `publish`: Publishes to PyPI after successful validation

### 2. `quick-ci.yml` - Pure3270 Quick CI
- **Triggers**: Push/PR to feature branches (excluding main/develop)
- **Purpose**: Fast feedback for development branches
- **Jobs**:
  - `quick-test`: Runs linting, formatting checks, and unit tests

### 3. `reports.yml` - Generate Reports
- **Triggers**: Push/PR to main branch, manual dispatch
- **Purpose**: Generate coverage reports and publish to GitHub Pages
- **Jobs**:
  - `generate-reports`: Creates coverage reports, linting reports, and deploys to GitHub Pages

### 4. `release.yml` - Create Release (NEW)
- **Triggers**: Push of version tags (v*.*.*)
- **Purpose**: Automatically create GitHub releases from version tags
- **Jobs**:
  - `create-release`: Validates version, generates release notes, and creates GitHub release

## Release Process

To create a new release:

1. **Update the version** in `pyproject.toml`:
   ```toml
   [project]
   version = "0.4.0"  # Update this line
   ```

2. **Update RELEASE_NOTES.md** (optional but recommended):
   Add a section for the new version with release notes.

3. **Commit and push** the version changes:
   ```bash
   git add pyproject.toml RELEASE_NOTES.md
   git commit -m "Bump version to 0.4.0"
   git push origin main
   ```

4. **Create and push a version tag**:
   ```bash
   git tag v0.4.0
   git push origin v0.4.0
   ```

5. **Automatic process**:
   - The `release.yml` workflow triggers and creates a GitHub release
   - The `ci.yml` workflow triggers on the release and publishes to PyPI
   - All tests must pass for the release to be published

## Workflow Dependencies

```
Tag Push (v*.*.*)
    ↓
release.yml (creates GitHub release)
    ↓
ci.yml (release validation & PyPI publish)
```

## Version Tag Format

The release workflow expects version tags in the format `v{major}.{minor}.{patch}`:
- `v1.0.0` - Major release
- `v0.3.1` - Minor/patch release
- `v1.0.0-beta` - Pre-release (marked as prerelease in GitHub)

## Release Notes Generation

The release workflow automatically generates release notes:

1. **First priority**: Looks for version-specific sections in `RELEASE_NOTES.md`
2. **Fallback**: Generates release notes from git commit history since the last tag
3. **Initial release**: Uses "Initial release" for repositories with no previous tags

## Testing Workflows Locally

You can test parts of the workflow logic locally:

```bash
# Test version extraction
python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])"

# Test that dependencies install correctly
pip install -e .[test]

# Run the test suite
python -m pytest tests/

# Run linting
python -m flake8 pure3270/
python -m black --check pure3270/
```
