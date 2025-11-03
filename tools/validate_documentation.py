#!/usr/bin/env python3
"""
Documentation validation and maintenance script for pure3270.

This script helps maintain the documentation organization by:
1. Validating that documentation files exist where expected
2. Checking for orphaned documentation files
3. Generating reports on documentation coverage
4. Suggesting improvements to documentation organization

Usage:
    python tools/validate_documentation.py [--check] [--report] [--fix]
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


class DocumentationValidator:
    """Validates and maintains documentation organization."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.issues: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def validate(self) -> bool:
        """Run all validation checks."""
        self.issues.clear()
        self.warnings.clear()
        self.info.clear()

        self._check_required_files()
        self._check_directory_structure()
        self._check_orphaned_files()
        self._check_naming_conventions()
        self._validate_index_completeness()

        return len(self.issues) == 0

    def _check_required_files(self) -> None:
        """Check that all required documentation files exist."""
        required_files = [
            "README.md",
            "CONTRIBUTING.md",
            "THIRD_PARTY_NOTICES.md",
            "DOCUMENTATION_INDEX.md",
            "docs/README.md",
            "memory-bank/activeContext.md",
            "memory-bank/productContext.md",
            "memory-bank/projectbrief.md",
            ".github/instructions/task-implementation.instructions.md",
        ]

        for file_path in required_files:
            full_path = self.root_dir / file_path
            if not full_path.exists():
                self.issues.append(f"Missing required file: {file_path}")

    def _check_directory_structure(self) -> None:
        """Check that documentation directories exist and are properly structured."""
        expected_dirs = [
            "docs/source",
            "docs/architecture",
            "docs/development",
            "docs/guides",
            "docs/testing",
            "docs/validation",
            "docs/reports",
            "memory-bank",
            "memory-bank/tasks",
            ".github/instructions",
            ".github/prompts",
            ".github/chatmodes",
            ".github/workflows",
        ]

        for dir_path in expected_dirs:
            full_path = self.root_dir / dir_path
            if not full_path.exists():
                self.warnings.append(f"Missing expected directory: {dir_path}")
            elif not full_path.is_dir():
                self.issues.append(f"Expected directory is a file: {dir_path}")

    def _check_orphaned_files(self) -> None:
        """Check for documentation files that might be in wrong locations."""
        # Files that should be moved to more appropriate locations
        orphaned_patterns = [
            ("*.SUMMARY.md", "Consider moving to docs/reports/"),
            ("*.REPORT.md", "Consider moving to docs/reports/"),
            ("test_*.py", "Test files should be in tests/ directory"),
            ("debug_*.py", "Debug scripts should be in scripts/ or archive/"),
        ]

        for pattern, suggestion in orphaned_patterns:
            for file_path in self.root_dir.rglob(pattern):
                if file_path.is_file() and not self._is_in_appropriate_location(
                    file_path
                ):
                    self.warnings.append(
                        f"Potentially orphaned file: {file_path.relative_to(self.root_dir)} - {suggestion}"
                    )

    def _is_in_appropriate_location(self, file_path: Path) -> bool:
        """Check if a file is in an appropriate location."""
        relative_path = file_path.relative_to(self.root_dir)

        # Test files should be in tests/
        if file_path.name.startswith("test_") and file_path.suffix == ".py":
            return str(relative_path).startswith("tests/")

        # Summary files are okay at root level
        if ".SUMMARY." in file_path.name:
            return True

        # Report files are okay at root level
        if ".REPORT." in file_path.name:
            return True

        # Debug scripts in scripts/ or archive/ are okay
        if file_path.name.startswith("debug_"):
            return str(relative_path).startswith("scripts/") or str(
                relative_path
            ).startswith("archive/")

        return True

    def _check_naming_conventions(self) -> None:
        """Check that files follow naming conventions."""
        for file_path in self.root_dir.rglob("*.md"):
            if file_path.is_file():
                filename = file_path.name

                # Summary files should be UPPER_CASE
                if "summary" in filename.lower() and not filename.isupper():
                    self.warnings.append(
                        f"Summary file should be UPPER_CASE: {file_path.relative_to(self.root_dir)}"
                    )

                # Report files should be UPPER_CASE
                if "report" in filename.lower() and not filename.isupper():
                    self.warnings.append(
                        f"Report file should be UPPER_CASE: {file_path.relative_to(self.root_dir)}"
                    )

    def _validate_index_completeness(self) -> None:
        """Validate that DOCUMENTATION_INDEX.md is complete."""
        index_file = self.root_dir / "DOCUMENTATION_INDEX.md"
        if not index_file.exists():
            self.issues.append("DOCUMENTATION_INDEX.md does not exist")
            return

        # Read the index file
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                index_content = f.read()
        except Exception as e:
            self.issues.append(f"Cannot read DOCUMENTATION_INDEX.md: {e}")
            return

        # Check for key sections
        required_sections = [
            "## Project Overview",
            "## User Documentation",
            "## Developer Documentation",
            "## Architecture & Design",
            "## Testing & Validation",
            "## CI/CD & Quality Assurance",
            "## MCP Server Documentation",
        ]

        for section in required_sections:
            if section not in index_content:
                self.warnings.append(
                    f"Missing section in DOCUMENTATION_INDEX.md: {section}"
                )

    def generate_report(self) -> str:
        """Generate a validation report."""
        report_lines = [
            "# Documentation Validation Report",
            f"Root Directory: {self.root_dir}",
            "",
        ]

        if self.issues:
            report_lines.extend(["## Issues (Must Fix)", ""])
            report_lines.extend(f"- {issue}" for issue in self.issues)
            report_lines.append("")

        if self.warnings:
            report_lines.extend(["## Warnings (Should Review)", ""])
            report_lines.extend(f"- {warning}" for warning in self.warnings)
            report_lines.append("")

        if self.info:
            report_lines.extend(["## Information", ""])
            report_lines.extend(f"- {info}" for info in self.info)
            report_lines.append("")

        if not self.issues and not self.warnings and not self.info:
            report_lines.extend(
                ["## Status: All Clear ✅", "", "No documentation issues found.", ""]
            )

        # Summary statistics
        total_files = len(list(self.root_dir.rglob("*.md")))
        report_lines.extend(
            [
                "## Summary Statistics",
                f"- Total Markdown files: {total_files}",
                f"- Issues: {len(self.issues)}",
                f"- Warnings: {len(self.warnings)}",
                f"- Info messages: {len(self.info)}",
            ]
        )

        return "\n".join(report_lines)

    def suggest_improvements(self) -> List[str]:
        """Suggest improvements to documentation organization."""
        suggestions = []

        # Check for missing directories
        missing_dirs = []
        for expected_dir in ["docs/guides", "docs/development", "docs/architecture"]:
            if not (self.root_dir / expected_dir).exists():
                missing_dirs.append(expected_dir)

        if missing_dirs:
            suggestions.append(f"Create missing directories: {', '.join(missing_dirs)}")

        # Check for files that could be better organized
        root_md_files = list(self.root_dir.glob("*.md"))
        if len(root_md_files) > 10:
            suggestions.append(
                "Consider moving some root-level .md files to appropriate subdirectories"
            )

        # Check for outdated summary files
        summary_files = list(self.root_dir.glob("*SUMMARY*.md"))
        if len(summary_files) > 5:
            suggestions.append("Consider consolidating or archiving old summary files")

        return suggestions


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate pure3270 documentation organization"
    )
    parser.add_argument("--check", action="store_true", help="Run validation checks")
    parser.add_argument(
        "--report", action="store_true", help="Generate validation report"
    )
    parser.add_argument("--fix", action="store_true", help="Attempt automatic fixes")
    parser.add_argument(
        "--root", type=Path, default=Path.cwd(), help="Project root directory"
    )

    args = parser.parse_args()

    # Default to check if no action specified
    if not any([args.check, args.report, args.fix]):
        args.check = True

    validator = DocumentationValidator(args.root)

    if args.check:
        is_valid = validator.validate()

        if validator.issues:
            print("❌ Documentation validation failed:")
            for issue in validator.issues:
                print(f"  - {issue}")
            return 1

        if validator.warnings:
            print("⚠️  Documentation validation warnings:")
            for warning in validator.warnings:
                print(f"  - {warning}")

        if is_valid and not validator.warnings:
            print("✅ Documentation validation passed!")

    if args.report:
        report = validator.generate_report()
        report_file = args.root / "DOCUMENTATION_VALIDATION_REPORT.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report generated: {report_file}")

        suggestions = validator.suggest_improvements()
        if suggestions:
            print("\n💡 Suggestions for improvement:")
            for suggestion in suggestions:
                print(f"  - {suggestion}")

    if args.fix:
        print("🔧 Automatic fixes not yet implemented")
        print("Manual fixes may be needed based on validation report")

    return 0 if not validator.issues else 1


if __name__ == "__main__":
    sys.exit(main())
