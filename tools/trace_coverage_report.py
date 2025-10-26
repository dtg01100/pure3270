#!/usr/bin/env python3
"""
Trace Coverage Report Generator

Generates comprehensive coverage reports for all trace files,
documenting which protocol features are tested by each trace.

Usage:
  trace_coverage_report.py [--traces-dir DIR] [--output FILE]
"""
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

# Reuse TraceAnalyzer from enhanced_trace_replay
sys.path.insert(0, str(Path(__file__).parent))
from enhanced_trace_replay import TraceAnalyzer, TraceFeatures


class TraceCoverageReport:
    """Generate coverage reports for trace files."""

    def __init__(self, traces_dir: str = "tests/data/traces"):
        self.traces_dir = Path(traces_dir)
        self.traces: Dict[str, TraceFeatures] = {}
        self.feature_coverage: Dict[str, List[str]] = defaultdict(list)

    def analyze_all_traces(self) -> None:
        """Analyze all trace files in directory."""
        if not self.traces_dir.exists():
            print(f"Traces directory not found: {self.traces_dir}")
            return

        trace_files = sorted(self.traces_dir.glob("*.trc"))
        print(f"Analyzing {len(trace_files)} trace files...")

        for trace_file in trace_files:
            print(f"  Analyzing {trace_file.name}...")
            analyzer = TraceAnalyzer(str(trace_file))
            if analyzer.load_trace():
                features = analyzer.analyze_features()
                self.traces[trace_file.name] = features

                # Build feature coverage map
                features_dict = features.to_dict()
                for feature, value in features_dict.items():
                    if isinstance(value, bool) and value:
                        self.feature_coverage[feature].append(trace_file.name)
                    elif isinstance(value, list) and value:
                        self.feature_coverage[feature].extend(
                            [trace_file.name] * len(value)
                        )

    def generate_summary(self) -> Dict[str, Any]:
        """Generate coverage summary."""
        total_traces = len(self.traces)

        summary = {
            "total_traces": total_traces,
            "feature_coverage": {},
            "traces_by_feature": {},
            "untested_features": [],
            "coverage_percentage": {},
        }

        # Calculate coverage for each feature type
        feature_categories = [
            "telnet_negotiation",
            "tn3270e",
            "bind_image",
            "printer",
            "extended_attributes",
            "structured_fields",
            "aid_codes",
            "error_conditions",
        ]

        for feature in feature_categories:
            traces_with_feature = set(self.feature_coverage.get(feature, []))
            count = len(traces_with_feature)
            percentage = (count / total_traces * 100) if total_traces > 0 else 0

            summary["feature_coverage"][feature] = {
                "traces_count": count,
                "percentage": round(percentage, 1),
                "traces": sorted(list(traces_with_feature)),
            }

            if count == 0:
                summary["untested_features"].append(feature)

        # Overall coverage percentage
        features_tested = sum(
            1 for f in feature_categories if len(self.feature_coverage.get(f, [])) > 0
        )
        summary["coverage_percentage"] = {
            "features_tested": features_tested,
            "total_features": len(feature_categories),
            "percentage": round((features_tested / len(feature_categories) * 100), 1),
        }

        # Traces by feature count
        summary["traces_by_feature"] = {}
        for trace_name, features in self.traces.items():
            feature_count = sum(
                1 for k, v in features.to_dict().items() if isinstance(v, bool) and v
            )
            summary["traces_by_feature"][trace_name] = feature_count

        return summary

    def print_text_report(self) -> None:
        """Print text report to stdout."""
        summary = self.generate_summary()

        print("\n" + "=" * 80)
        print("TRACE FILE COVERAGE REPORT")
        print("=" * 80)

        print(f"\nTotal Trace Files: {summary['total_traces']}")
        print(
            f"Overall Feature Coverage: {summary['coverage_percentage']['features_tested']}/{summary['coverage_percentage']['total_features']} ({summary['coverage_percentage']['percentage']}%)"
        )

        print("\n" + "-" * 80)
        print("FEATURE COVERAGE BREAKDOWN")
        print("-" * 80)

        for feature, data in sorted(summary["feature_coverage"].items()):
            status = "✓" if data["traces_count"] > 0 else "✗"
            print(f"\n{status} {feature.upper().replace('_', ' ')}")
            print(f"   Traces: {data['traces_count']} ({data['percentage']}%)")
            if data["traces"]:
                print(f"   Files: {', '.join(data['traces'][:5])}")
                if len(data["traces"]) > 5:
                    print(f"          ... and {len(data['traces']) - 5} more")

        if summary["untested_features"]:
            print("\n" + "-" * 80)
            print("UNTESTED FEATURES")
            print("-" * 80)
            for feature in summary["untested_features"]:
                print(f"  ✗ {feature.replace('_', ' ').title()}")

        print("\n" + "-" * 80)
        print("TOP 10 MOST COMPREHENSIVE TRACES")
        print("-" * 80)
        traces_sorted = sorted(
            summary["traces_by_feature"].items(), key=lambda x: x[1], reverse=True
        )
        for trace, count in traces_sorted[:10]:
            print(f"  {trace}: {count} features")

        print("\n" + "=" * 80)

    def save_json_report(self, output_file: str) -> None:
        """Save JSON report to file."""
        summary = self.generate_summary()

        # Add full trace details
        summary["trace_details"] = {}
        for trace_name, features in self.traces.items():
            summary["trace_details"][trace_name] = features.to_dict()

        with open(output_file, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\nJSON report saved to: {output_file}")

    def generate_markdown_report(self, output_file: str) -> None:
        """Generate markdown coverage report."""
        summary = self.generate_summary()

        lines = [
            "# Trace File Coverage Report",
            "",
            f"**Generated:** {Path(output_file).name}",
            f"**Total Traces:** {summary['total_traces']}",
            f"**Feature Coverage:** {summary['coverage_percentage']['percentage']}%",
            "",
            "## Feature Coverage Overview",
            "",
            "| Feature | Traces | Coverage | Status |",
            "|---------|--------|----------|--------|",
        ]

        for feature, data in sorted(summary["feature_coverage"].items()):
            status = "✅ Tested" if data["traces_count"] > 0 else "❌ Untested"
            feature_name = feature.replace("_", " ").title()
            lines.append(
                f"| {feature_name} | {data['traces_count']} | {data['percentage']}% | {status} |"
            )

        lines.extend(["", "## Untested Features", ""])

        if summary["untested_features"]:
            for feature in summary["untested_features"]:
                lines.append(f"- ❌ {feature.replace('_', ' ').title()}")
        else:
            lines.append("✅ All features have at least some test coverage!")

        lines.extend(
            [
                "",
                "## Top 10 Most Comprehensive Traces",
                "",
                "| Rank | Trace File | Features |",
                "|------|------------|----------|",
            ]
        )

        traces_sorted = sorted(
            summary["traces_by_feature"].items(), key=lambda x: x[1], reverse=True
        )
        for idx, (trace, count) in enumerate(traces_sorted[:10], 1):
            lines.append(f"| {idx} | {trace} | {count} |")

        lines.extend(["", "## Feature Details", ""])

        for feature, data in sorted(summary["feature_coverage"].items()):
            feature_name = feature.replace("_", " ").title()
            lines.append(f"### {feature_name}")
            lines.append(f"- **Traces:** {data['traces_count']}")
            lines.append(f"- **Coverage:** {data['percentage']}%")
            if data["traces"]:
                lines.append("- **Files:**")
                for trace in sorted(data["traces"]):
                    lines.append(f"  - `{trace}`")
            lines.append("")

        with open(output_file, "w") as f:
            f.write("\n".join(lines))

        print(f"Markdown report saved to: {output_file}")


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate trace coverage report")
    parser.add_argument(
        "--traces-dir",
        default="tests/data/traces",
        help="Directory containing trace files",
    )
    parser.add_argument(
        "--output", help="Output file (JSON or Markdown based on extension)"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format",
    )

    args = parser.parse_args()

    reporter = TraceCoverageReport(args.traces_dir)
    reporter.analyze_all_traces()

    if args.output:
        if args.output.endswith(".json") or args.format == "json":
            reporter.save_json_report(args.output)
        elif args.output.endswith(".md") or args.format == "markdown":
            reporter.generate_markdown_report(args.output)
        else:
            reporter.print_text_report()
    else:
        reporter.print_text_report()


if __name__ == "__main__":
    main()
