#!/usr/bin/env python3
"""
DRY (Don't Repeat Yourself) Violation Detection Tool for Pure3270

This tool detects code duplications and repetitive patterns in the codebase.
It provides automated detection of DRY violations with configurable thresholds
and integration with pre-commit hooks for prevention.

Usage:
    python tools/dry_violation_detector.py
    python tools/dry_violation_detector.py --min-lines 5 --output json
    python tools/dry_violation_detector.py --check-only
"""

import argparse
import ast
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


class DRYViolationDetector:
    """Detects DRY violations in Python code."""

    def __init__(
        self,
        base_path: str = ".",
        min_lines: int = 4,
        min_characters: int = 100,
        exclude_dirs: List[str] | None = None,
    ):
        self.base_path = Path(base_path)
        self.min_lines = min_lines
        self.min_characters = min_characters
        self.exclude_dirs = exclude_dirs or [
            "__pycache__",
            ".git",
            ".pytest_cache",
            "build",
            "dist",
            "archive",
            "venv",
            ".venv",
        ]

    def find_python_files(self) -> List[Path]:
        """Find all Python files excluding specified directories."""
        files = []
        for py_file in self.base_path.rglob("*.py"):
            # Check if file is in excluded directory
            if any(excluded in py_file.parts for excluded in self.exclude_dirs):
                continue
            files.append(py_file)
        return files

    def analyze_file_ast(self, file_path: Path) -> Tuple[ast.AST | None, str]:
        """Parse file and return AST and source code."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()

            tree = ast.parse(source_code, filename=str(file_path))
            return tree, source_code
        except (SyntaxError, UnicodeDecodeError, OSError) as e:
            print(f"Warning: Could not parse {file_path}: {e}")
            return None, ""

    def extract_function_signatures(self, tree: ast.AST | None, source_code: str) -> List[Dict]:  # type: ignore
        """Extract function/method signatures for comparison."""
        signatures: List[Dict] = []
        if tree is None:
            return signatures

        try:
            lines = source_code.splitlines()

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Get function signature
                    try:
                        func_line = lines[node.lineno - 1].strip()
                        # Clean up the signature for comparison
                        signature = self._clean_function_signature(func_line)
                        if (
                            signature and len(signature) > 20
                        ):  # Only significant signatures
                            signatures.append(
                                {
                                    "name": node.name,
                                    "line": node.lineno,
                                    "signature": signature,
                                    "length": len(signature),
                                }
                            )
                    except (IndexError, AttributeError):
                        continue
        except Exception as e:
            print(f"Error extracting signatures from {tree}: {e}")

        return signatures

    def _clean_function_signature(self, signature: str) -> str:
        """Clean function signature for comparison."""
        # Remove default values
        signature = re.sub(r"=\s*[^,\)]+", "=", signature)
        # Remove comments
        signature = re.sub(r"#.*$", "", signature)
        # Normalize whitespace
        signature = re.sub(r"\s+", " ", signature).strip()
        return signature

    def find_code_blocks(self, source_code: str, min_lines: int | None = None) -> List[Dict]:  # type: ignore
        """Find significant code blocks for comparison."""
        if min_lines is None:
            min_lines = self.min_lines

        blocks: List[Dict] = []
        lines = source_code.splitlines()

        # Skip empty lines at beginning and end
        meaningful_lines = [
            line for line in lines if line.strip() and not line.strip().startswith("#")
        ]

        for i in range(len(meaningful_lines) - min_lines + 1):
            block_lines = meaningful_lines[i : i + min_lines]
            block_text = "\n".join(block_lines)

            # Check minimum character count
            if len(block_text) < self.min_characters:
                continue

            # Skip blocks that are mostly comments
            comment_ratio = sum(
                1 for line in block_lines if line.strip().startswith("#")
            ) / len(block_lines)
            if comment_ratio > 0.5:
                continue

            # Create hash for comparison (non-security fingerprint)
            # Use usedforsecurity=False to avoid bandit warning about MD5
            block_hash = hashlib.md5(
                block_text.encode(), usedforsecurity=False
            ).hexdigest()  # nosec B324
            blocks.append(
                {
                    "hash": block_hash,
                    "text": block_text,
                    "line_count": len(block_lines),
                    "char_count": len(block_text),
                }
            )

        return blocks

    def detect_violations(self) -> Dict:  # type: ignore
        """Detect DRY violations in the codebase."""
        python_files = self.find_python_files()
        violations = {
            "summary": {
                "total_files": len(python_files),
                "total_violations": 0,
                "severity_distribution": {"high": 0, "medium": 0, "low": 0},
            },
            "file_violations": {},
            "function_violations": {},
            "pattern_violations": [],
        }

        # Track code blocks across files
        file_blocks = {}
        file_signatures = {}
        all_blocks = defaultdict(list)
        all_signatures = defaultdict(list)

        for file_path in python_files:
            relative_path = str(file_path.relative_to(self.base_path))
            print(f"Analyzing: {relative_path}")

            tree, source_code = self.analyze_file_ast(file_path)

            # Find code blocks
            if source_code:
                blocks = self.find_code_blocks(source_code)
                file_blocks[relative_path] = blocks

                # Add blocks to global tracking
                for block in blocks:
                    all_blocks[block["hash"]].append(
                        {
                            "file": relative_path,
                            "block": block,
                        }
                    )

            # Find function signatures
            if tree:
                signatures = self.extract_function_signatures(tree, source_code)
                file_signatures[relative_path] = signatures

                # Add signatures to global tracking
                for sig in signatures:
                    key = f"{sig['name']}:{str(sig['signature'])[:50]}"
                    all_signatures[key].append(
                        {
                            "file": relative_path,
                            "signature": sig,
                        }
                    )

        # Analyze violations
        violations = self._analyze_violations(all_blocks, all_signatures, violations)
        return violations  # type: ignore

    def _analyze_violations(
        self, all_blocks: Dict, all_signatures: Dict, violations: Dict
    ) -> Dict:  # type: ignore
        """Analyze detected violations and categorize them."""

        # Code block duplications
        for block_hash, locations in all_blocks.items():
            if len(locations) > 1:
                violation = {
                    "type": "code_block_duplication",
                    "occurrences": len(locations),
                    "locations": locations,
                    "block_size": locations[0]["block"]["line_count"],
                    "char_count": locations[0]["block"]["char_count"],
                    "severity": self._calculate_severity(
                        locations[0]["block"]["line_count"],
                        locations[0]["block"]["char_count"],
                        len(locations),
                    ),
                }
                violations["pattern_violations"].append(violation)
                violations["summary"]["total_violations"] += 1
                violations["summary"]["severity_distribution"][
                    violation["severity"]
                ] += 1

        # Function signature duplications
        for sig_key, locations in all_signatures.items():
            if len(locations) > 1:
                violation = {
                    "type": "function_signature_duplication",
                    "occurrences": len(locations),
                    "locations": locations,
                    "function_name": locations[0]["signature"]["name"],
                    "severity": "medium",  # Function duplications are typically medium severity
                }
                violations["function_violations"][sig_key] = violation
                violations["summary"]["total_violations"] += 1
                violations["summary"]["severity_distribution"]["medium"] += 1

        return violations

    def _calculate_severity(
        self, line_count: int, char_count: int, occurrences: int
    ) -> str:
        """Calculate violation severity based on size and frequency."""
        # High severity: Large blocks duplicated many times
        if line_count >= 10 and char_count >= 500 and occurrences >= 2:
            return "high"

        # Medium severity: Medium blocks or high frequency
        if line_count >= 6 and char_count >= 200 and occurrences >= 2:
            return "medium"

        # Low severity: Small blocks or single duplication
        return "low"

    def save_report(self, violations: Dict, output_path: str) -> None:  # type: ignore
        """Save violations report to file."""
        report_data = {
            "metadata": {
                "generated_at": self._get_timestamp(),
                "base_path": str(self.base_path),
                "min_lines": self.min_lines,
                "min_characters": self.min_characters,
                "version": "1.0.0",
            },
            "violations": violations,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime

        return datetime.utcnow().isoformat() + "Z"

    def print_summary(self, violations: Dict) -> None:  # type: ignore
        """Print a human-readable summary of violations."""
        summary = violations["summary"]

        print("\n" + "=" * 60)
        print("🔍 DRY VIOLATION DETECTION REPORT")
        print("=" * 60)
        print(f"Files analyzed: {summary['total_files']}")
        print(f"Total violations: {summary['total_violations']}")
        print(f"Severity distribution:")
        print(f"  🔴 High: {summary['severity_distribution']['high']}")
        print(f"  🟡 Medium: {summary['severity_distribution']['medium']}")
        print(f"  🟢 Low: {summary['severity_distribution']['low']}")

        if violations["pattern_violations"]:
            print(f"\n🚨 Pattern Violations: {len(violations['pattern_violations'])}")
            for i, violation in enumerate(violations["pattern_violations"][:5], 1):
                print(
                    f"  {i}. {violation['type']} - {violation['occurrences']} occurrences"
                )
                if violation["severity"] == "high":
                    print(
                        f"     🔴 High severity: {violation['block_size']} lines, {violation['char_count']} chars"
                    )
                elif violation["severity"] == "medium":
                    print(
                        f"     🟡 Medium severity: {violation['block_size']} lines, {violation['char_count']} chars"
                    )
                else:
                    print(
                        f"     🟢 Low severity: {violation['block_size']} lines, {violation['char_count']} chars"
                    )

        if violations["function_violations"]:
            print(f"\n⚙️ Function Violations: {len(violations['function_violations'])}")
            for sig_key, violation in list(violations["function_violations"].items())[
                :5
            ]:
                print(
                    f"  • {violation['function_name']} - {violation['occurrences']} occurrences"
                )

        if summary["total_violations"] == 0:
            print("\n✅ No DRY violations detected!")

    def check_threshold_violations(self, violations: Dict) -> bool:  # type: ignore
        """Check if violations exceed acceptable thresholds."""
        summary = violations["summary"]

        # Define acceptable thresholds
        high_severity_threshold = 0
        medium_severity_threshold = 3
        total_violations_threshold = 5

        has_violations = (
            summary["severity_distribution"]["high"] > high_severity_threshold
            or summary["severity_distribution"]["medium"] > medium_severity_threshold
            or summary["total_violations"] > total_violations_threshold
        )

        if has_violations:
            print(f"\n❌ DRY VIOLATION THRESHOLD EXCEEDED")
            print(
                f"   High severity violations: {summary['severity_distribution']['high']} (limit: {high_severity_threshold})"
            )
            print(
                f"   Medium severity violations: {summary['severity_distribution']['medium']} (limit: {medium_severity_threshold})"
            )
            print(
                f"   Total violations: {summary['total_violations']} (limit: {total_violations_threshold})"
            )
            return True

        return False


def main():
    parser = argparse.ArgumentParser(
        description="DRY Violation Detection Tool for Pure3270"
    )
    parser.add_argument("--base-path", default=".", help="Base path to analyze")
    parser.add_argument(
        "--min-lines", type=int, default=4, help="Minimum lines for a code block"
    )
    parser.add_argument(
        "--min-chars", type=int, default=100, help="Minimum characters for a code block"
    )
    parser.add_argument(
        "--output", choices=["console", "json"], default="console", help="Output format"
    )
    parser.add_argument("--output-file", help="Output file path for JSON reports")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check thresholds, don't report details",
    )
    parser.add_argument(
        "--exclude", nargs="*", help="Additional directories to exclude"
    )

    args = parser.parse_args()

    detector = DRYViolationDetector(
        base_path=args.base_path,
        min_lines=args.min_lines,
        min_characters=args.min_chars,
        exclude_dirs=["__pycache__", ".git"] + (args.exclude or []),
    )

    print("🔍 Starting DRY violation detection...")
    violations = detector.detect_violations()

    if args.check_only:
        threshold_exceeded = detector.check_threshold_violations(violations)
        if threshold_exceeded:
            print(
                "DRY violation thresholds exceeded. Run without --check-only for details."
            )
            return 1

    if args.output == "json":
        output_file = args.output_file or "dry_violations_report.json"
        detector.save_report(violations, output_file)
        print(f"📄 Report saved to: {output_file}")
    else:
        detector.print_summary(violations)

    return 0 if violations["summary"]["total_violations"] == 0 else 1


if __name__ == "__main__":
    exit(main())
