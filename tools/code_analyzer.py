#!/usr/bin/env python3
"""
Code Analysis Tool for Pure3270

Analyzes code quality, complexity, and duplication in the pure3270 codebase.
Uses radon for complexity analysis and provides insights for refactoring.

Usage:
    python code_analyzer.py
    python code_analyzer.py --focus pure3270/protocol/
    python code_analyzer.py --complexity-only
"""

import argparse
from pathlib import Path
from typing import Dict, List

try:
    import radon.complexity as radon_cc

    RADON_AVAILABLE = True
except ImportError:
    RADON_AVAILABLE = False

try:
    from cohesion import analyze_file

    COHESION_AVAILABLE = True
except ImportError:
    COHESION_AVAILABLE = False


class CodeAnalyzer:
    """Code analysis tool for pure3270."""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.pure3270_path = self.base_path / "pure3270"

    def analyze_complexity(self) -> Dict:
        """Analyze code complexity using radon."""
        if not RADON_AVAILABLE:
            return {"error": "radon not available"}

        results = {
            "files_analyzed": 0,
            "functions": [],
            "classes": [],
            "complexity_warnings": [],
            "summary": {},
        }

        # Analyze Python files
        for py_file in self._find_python_files():
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Analyze complexity
                blocks = radon_cc.cc_visit(content)

                for block in blocks:
                    block_info = {
                        "file": str(py_file.relative_to(self.base_path)),
                        "name": block.name,
                        "complexity": block.complexity,
                        "type": block.block_type,
                        "line": block.lineno,
                    }

                    if block.block_type == "function":
                        results["functions"].append(block_info)
                    elif block.block_type == "class":
                        results["classes"].append(block_info)

                    # Flag high complexity
                    if block.complexity > 10:
                        results["complexity_warnings"].append(
                            {
                                **block_info,
                                "severity": (
                                    "high" if block.complexity > 15 else "medium"
                                ),
                            }
                        )

                results["files_analyzed"] += 1

            except Exception as e:
                print(f"Error analyzing {py_file}: {e}")

        # Generate summary
        results["summary"] = self._generate_complexity_summary(results)
        return results

    def analyze_cohesion(self) -> Dict:
        """Analyze code cohesion."""
        if not COHESION_AVAILABLE:
            return {"error": "cohesion not available"}

        results = {"files_analyzed": 0, "cohesion_scores": [], "low_cohesion_files": []}

        for py_file in self._find_python_files():
            try:
                analysis = analyze_file(str(py_file))

                file_score = {
                    "file": str(py_file.relative_to(self.base_path)),
                    "cohesion": analysis.cohesion,
                    "functions": len(analysis.functions),
                    "classes": len(analysis.classes),
                }

                results["cohesion_scores"].append(file_score)

                # Flag low cohesion
                if analysis.cohesion < 0.5:
                    results["low_cohesion_files"].append(file_score)

                results["files_analyzed"] += 1

            except Exception as e:
                print(f"Error analyzing cohesion for {py_file}: {e}")

        return results

    def find_duplications(self) -> Dict:
        """Find potential code duplications."""
        # Simple duplication detection based on line similarity
        results = {"duplicate_blocks": [], "similar_functions": []}

        # This is a basic implementation - could be enhanced with more sophisticated tools
        file_contents = {}

        for py_file in self._find_python_files():
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    file_contents[str(py_file.relative_to(self.base_path))] = lines
            except Exception as e:
                print(f"Error reading {py_file}: {e}")

        # Look for identical blocks of 5+ lines
        blocks = {}
        for filename, lines in file_contents.items():
            for i in range(len(lines) - 5):
                block = tuple(lines[i : i + 5])
                if block in blocks:
                    blocks[block].append((filename, i))
                else:
                    blocks[block] = [(filename, i)]

        # Report duplicates
        for block, locations in blocks.items():
            if len(locations) > 1:
                results["duplicate_blocks"].append(
                    {
                        "block": "".join(block),
                        "locations": locations,
                        "occurrences": len(locations),
                    }
                )

        return results

    def _find_python_files(self) -> List[Path]:
        """Find all Python files in the pure3270 directory."""
        if not self.pure3270_path.exists():
            return []

        return list(self.pure3270_path.rglob("*.py"))

    def _generate_complexity_summary(self, results: Dict) -> Dict:
        """Generate summary statistics for complexity analysis."""
        functions = results["functions"]
        classes = results["classes"]

        return {
            "total_functions": len(functions),
            "total_classes": len(classes),
            "avg_function_complexity": (
                sum(f["complexity"] for f in functions) / len(functions)
                if functions
                else 0
            ),
            "avg_class_complexity": (
                sum(c["complexity"] for c in classes) / len(classes) if classes else 0
            ),
            "high_complexity_functions": len(
                [f for f in functions if f["complexity"] > 15]
            ),
            "high_complexity_classes": len(
                [c for c in classes if c["complexity"] > 15]
            ),
            "complexity_warnings": len(results["complexity_warnings"]),
        }

    def display_results(self, results: Dict, analysis_type: str):
        """Display analysis results."""
        if analysis_type == "complexity":
            self._display_complexity_results(results)
        elif analysis_type == "cohesion":
            self._display_cohesion_results(results)
        elif analysis_type == "duplication":
            self._display_duplication_results(results)

    def _display_complexity_results(self, results: Dict):
        """Display complexity analysis results."""
        if "error" in results:
            print(f"Complexity analysis not available: {results['error']}")
            return

        print("🔍 Code Complexity Analysis")
        print("=" * 50)

        summary = results["summary"]
        print(f"Files analyzed: {results['files_analyzed']}")
        print(f"Total functions: {summary['total_functions']}")
        print(f"Total classes: {summary['total_classes']}")
        print(f"Average function complexity: {summary['avg_function_complexity']:.2f}")
        print(f"Average class complexity: {summary['avg_class_complexity']:.2f}")
        print(
            f"High complexity functions (>15): {summary['high_complexity_functions']}"
        )
        print(f"High complexity classes (>15): {summary['high_complexity_classes']}")
        print(f"Complexity warnings: {summary['complexity_warnings']}")

        if results["complexity_warnings"]:
            print("\n⚠️  High Complexity Functions:")
            for warning in results["complexity_warnings"][:10]:  # Show top 10
                print(
                    f"  • {warning['file']}:{warning['line']} - {warning['name']} (complexity: {warning['complexity']})"
                )

    def _display_cohesion_results(self, results: Dict):
        """Display cohesion analysis results."""
        if "error" in results:
            print(f"Cohesion analysis not available: {results['error']}")
            return

        print("🔗 Code Cohesion Analysis")
        print("=" * 50)

        print(f"Files analyzed: {results['files_analyzed']}")

        if results["cohesion_scores"]:
            avg_cohesion = sum(s["cohesion"] for s in results["cohesion_scores"]) / len(
                results["cohesion_scores"]
            )
            print(f"Average cohesion: {avg_cohesion:.3f}")

        if results["low_cohesion_files"]:
            print(
                f"\n⚠️  Low Cohesion Files (< 0.5): {len(results['low_cohesion_files'])}"
            )
            for file_info in results["low_cohesion_files"][:5]:  # Show top 5
                print(
                    f"  • {file_info['file']}: {file_info['cohesion']:.3f} ({file_info['functions']} functions, {file_info['classes']} classes)"
                )

    def _display_duplication_results(self, results: Dict):
        """Display duplication analysis results."""
        print("📋 Code Duplication Analysis")
        print("=" * 50)

        if results["duplicate_blocks"]:
            print(f"Found {len(results['duplicate_blocks'])} duplicate code blocks:")

            for i, dup in enumerate(results["duplicate_blocks"][:5]):  # Show top 5
                print(f"\nDuplicate Block {i+1} (occurs {dup['occurrences']} times):")
                print("Locations:")
                for loc in dup["locations"]:
                    print(f"  • {loc[0]}:{loc[1]}")
                print("Code:")
                for line in dup["block"].split("\n")[:3]:  # Show first 3 lines
                    print(f"  {line.rstrip()}")
                if len(dup["block"].split("\n")) > 3:
                    print("  ...")
        else:
            print("No significant code duplications found.")


def main():
    parser = argparse.ArgumentParser(description="Code Analysis Tool for Pure3270")
    parser.add_argument("--focus", help="Focus on specific directory")
    parser.add_argument(
        "--complexity-only", action="store_true", help="Run only complexity analysis"
    )
    parser.add_argument(
        "--cohesion-only", action="store_true", help="Run only cohesion analysis"
    )
    parser.add_argument(
        "--duplication-only", action="store_true", help="Run only duplication analysis"
    )

    args = parser.parse_args()

    base_path = args.focus if args.focus else "."
    analyzer = CodeAnalyzer(base_path)

    if args.complexity_only:
        results = analyzer.analyze_complexity()
        analyzer.display_results(results, "complexity")
    elif args.cohesion_only:
        results = analyzer.analyze_cohesion()
        analyzer.display_results(results, "cohesion")
    elif args.duplication_only:
        results = analyzer.find_duplications()
        analyzer.display_results(results, "duplication")
    else:
        # Run all analyses
        print("Running complete code analysis...\n")

        complexity_results = analyzer.analyze_complexity()
        analyzer.display_results(complexity_results, "complexity")
        print()

        cohesion_results = analyzer.analyze_cohesion()
        analyzer.display_results(cohesion_results, "cohesion")
        print()

        duplication_results = analyzer.find_duplications()
        analyzer.display_results(duplication_results, "duplication")


if __name__ == "__main__":
    main()
