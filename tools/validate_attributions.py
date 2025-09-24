#!/usr/bin/env python3
"""
Attribution Validation Tool for Pure3270

This tool validates attribution comments throughout the codebase to ensure:
- All attribution comments follow correct format
- Required information is present
- License compatibility is maintained
- Integration with documentation systems

Usage:
    python tools/validate_attributions.py --check-all
    python tools/validate_attributions.py --check-file pure3270/protocol/tn3270.py
    python tools/validate_attributions.py --interactive
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import our validation system
from tests.test_attribution_validation import AttributionValidator


class AttributionChecker:
    """Checks attribution comments in the codebase."""

    def __init__(self):
        """Initialize the attribution checker."""
        self.validator = AttributionValidator()
        self.issues: List[Dict[str, Any]] = []

    def find_attribution_comments(self, file_path: Path) -> List[Dict[str, Any]]:
        """Find attribution comments in a file."""
        if not file_path.exists():
            return []

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Skip binary files
            return []

        attributions = []

        # Look for module-level attribution blocks
        module_pattern = r"ATTRIBUTION NOTICE.*?ATTRIBUTION REQUIREMENTS"
        module_matches = re.finditer(module_pattern, content, re.DOTALL)
        for match in module_matches:
            attributions.append(
                {
                    "type": "module",
                    "content": match.group(0),
                    "start_line": content[: match.start()].count("\n") + 1,
                    "end_line": content[: match.end()].count("\n") + 1,
                }
            )

        # Look for function-level attribution (docstrings)
        function_pattern = r'""".*?Ported from.*?\n.*?Licensed under.*?\n.*?\n.*?"""'
        function_matches = re.finditer(function_pattern, content, re.DOTALL)
        for match in function_matches:
            attributions.append(
                {
                    "type": "function",
                    "content": match.group(0),
                    "start_line": content[: match.start()].count("\n") + 1,
                    "end_line": content[: match.end()].count("\n") + 1,
                }
            )

        return attributions

    def validate_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate attribution comments in a single file."""
        file_issues = []

        try:
            attributions = self.find_attribution_comments(file_path)

            for i, attribution in enumerate(attributions):
                if attribution["type"] == "module":
                    result = self.validator.validate_module_attribution(
                        attribution["content"]
                    )
                elif attribution["type"] == "function":
                    result = self.validator.validate_function_attribution(
                        attribution["content"]
                    )
                else:
                    continue

                if not result["valid"]:
                    file_issues.append(
                        {
                            "file": str(file_path),
                            "line": attribution["start_line"],
                            "type": attribution["type"],
                            "issues": result["issues"],
                            "score": result["score"],
                        }
                    )

        except Exception as e:
            file_issues.append(
                {
                    "file": str(file_path),
                    "line": 0,
                    "type": "error",
                    "issues": [f"Error reading file: {e}"],
                    "score": 0,
                }
            )

        return {
            "file": str(file_path),
            "total_attributions": len(attributions),
            "valid_attributions": len(attributions) - len(file_issues),
            "issues": file_issues,
        }

    def check_directory(
        self, directory: Path, pattern: str = "*.py"
    ) -> List[Dict[str, Any]]:
        """Check all files in a directory."""
        results = []

        for file_path in directory.rglob(pattern):
            if file_path.is_file():
                result = self.validate_file(file_path)
                results.append(result)

        return results

    def generate_report(self, results: List[Dict[str, Any]]) -> str:
        """Generate a summary report of validation results."""
        total_files = len(results)
        total_issues = sum(len(r["issues"]) for r in results)
        total_attributions = sum(r["total_attributions"] for r in results)
        valid_attributions = sum(r["valid_attributions"] for r in results)

        report = []
        report.append("ATTRIBUTION VALIDATION REPORT")
        report.append("=" * 50)
        report.append(f"Files checked: {total_files}")
        report.append(f"Total attributions found: {total_attributions}")
        report.append(f"Valid attributions: {valid_attributions}")
        report.append(
            f"Invalid attributions: {total_attributions - valid_attributions}"
        )
        report.append(f"Total issues: {total_issues}")
        report.append("")

        if total_issues > 0:
            report.append("ISSUES FOUND:")
            report.append("-" * 20)

            for result in results:
                if result["issues"]:
                    report.append(f"\nFile: {result['file']}")
                    for issue in result["issues"]:
                        report.append(f"  Line {issue['line']} ({issue['type']}):")
                        for problem in issue["issues"]:
                            report.append(f"    - {problem}")
                        report.append(f"    Score: {issue['score']}/10")
        else:
            report.append("✅ All attribution comments are valid!")

        report.append("")
        report.append("RECOMMENDATIONS:")
        report.append("-" * 20)
        report.append(
            "• Use 'python tools/generate_attribution.py --interactive' to create new attributions"
        )
        report.append(
            "• Run 'python -m pytest tests/test_attribution_validation.py' for detailed validation"
        )
        report.append(
            "• See 'tools/ATTRIBUTION_GUIDE.md' for comprehensive documentation"
        )

        return "\n".join(report)


def main():
    """Main entry point for attribution validation."""
    parser = argparse.ArgumentParser(
        description="Validate attribution comments in Pure3270 codebase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --check-all
  %(prog)s --check-file pure3270/protocol/tn3270.py
  %(prog)s --check-dir pure3270/protocol/
  %(prog)s --interactive
        """,
    )

    parser.add_argument(
        "--check-all", action="store_true", help="Check all Python files in the project"
    )
    parser.add_argument("--check-file", help="Check a specific file")
    parser.add_argument("--check-dir", help="Check all files in a directory")
    parser.add_argument(
        "--pattern", default="*.py", help="File pattern to check (default: *.py)"
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactive mode for fixing issues",
    )

    args = parser.parse_args()

    checker = AttributionChecker()

    if args.check_all:
        print("Checking all Python files in the project...")
        results = checker.check_directory(Path("."))
        report = checker.generate_report(results)
        print(report)

        # Exit with error code if issues found
        total_issues = sum(len(r["issues"]) for r in results)
        sys.exit(1 if total_issues > 0 else 0)

    elif args.check_file:
        file_path = Path(args.check_file)
        result = checker.validate_file(file_path)
        report = checker.generate_report([result])
        print(report)

        # Exit with error code if issues found
        sys.exit(1 if result["issues"] else 0)

    elif args.check_dir:
        directory = Path(args.check_dir)
        print(f"Checking directory: {directory}")
        results = checker.check_directory(directory, args.pattern)
        report = checker.generate_report(results)
        print(report)

        # Exit with error code if issues found
        total_issues = sum(len(r["issues"]) for r in results)
        sys.exit(1 if total_issues > 0 else 0)

    elif args.interactive:
        print("Interactive attribution validation mode")
        print("This feature will help you identify and fix attribution issues.")
        print()

        # For now, just run check-all
        results = checker.check_directory(Path("."))
        report = checker.generate_report(results)
        print(report)

        if sum(len(r["issues"]) for r in results) > 0:
            print("\nTo fix issues:")
            print(
                "1. Use 'python tools/generate_attribution.py --interactive' to create new attributions"
            )
            print(
                "2. Run 'python -m pytest tests/test_attribution_validation.py' for detailed validation"
            )
            print("3. See 'tools/ATTRIBUTION_GUIDE.md' for comprehensive documentation")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
