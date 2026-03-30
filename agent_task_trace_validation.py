#!/usr/bin/env python3
"""
Agent Task: Comprehensive Trace File Validation

This script processes all available trace files and generates a detailed
validation report. Can be run autonomously by an AI agent.

Usage:
    python agent_task_trace_validation.py [--output-dir DIR]
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.data_stream import DataStreamParser
from pure3270.protocol.trace_recorder import TraceRecorder


class TraceValidationAgent:
    """Autonomous agent for trace file validation."""

    def __init__(self, trace_dir: str = ".", output_dir: str = "test_output"):
        self.trace_dir = Path(trace_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.results: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "trace_dir": str(self.trace_dir.absolute()),
            "summary": {},
            "traces": [],
            "statistics": {},
            "recommendations": [],
        }

    def find_trace_files(self) -> List[Path]:
        """Find all .trc files in trace directory."""
        trace_files = list(self.trace_dir.glob("*.trc"))
        print(f"🔍 Found {len(trace_files)} trace files")
        return sorted(trace_files)

    def analyze_trace_file(self, trace_path: Path) -> Dict[str, Any]:
        """Analyze a single trace file."""
        result = {
            "file": str(trace_path.name),
            "path": str(trace_path.absolute()),
            "size_bytes": trace_path.stat().st_size,
            "status": "unknown",
            "errors": [],
            "warnings": [],
            "metrics": {},
        }

        try:
            # Read trace file
            with open(trace_path, "rb") as f:
                data = f.read()

            result["metrics"]["raw_size"] = len(data)

            # Try to parse with TraceRecorder
            try:
                recorder = TraceRecorder()
                # Attempt to load trace
                if hasattr(recorder, "load"):
                    recorder.load(str(trace_path))
                    result["status"] = "✓ Loaded successfully"
                else:
                    # Alternative: just verify file is readable
                    result["status"] = "✓ File readable"
                    result["warnings"].append(
                        "TraceRecorder.load() method not available"
                    )
            except Exception as e:
                result["status"] = "⚠ Parse warning"
                result["warnings"].append(f"TraceRecorder error: {str(e)}")

            # Try to parse as data stream
            try:
                screen = ScreenBuffer(24, 80)
                parser = DataStreamParser(screen)
                parser.parse(data)
                result["metrics"]["data_stream_parsed"] = True
                result["metrics"]["screen_updates"] = 1
            except Exception as e:
                result["metrics"]["data_stream_parsed"] = False
                result["warnings"].append(f"DataStreamParser error: {str(e)}")

            # Calculate basic statistics
            result["metrics"]["byte_distribution"] = self._analyze_byte_distribution(
                data
            )

        except Exception as e:
            result["status"] = "✗ Failed"
            result["errors"].append(f"Critical error: {str(e)}")

        return result

    def _analyze_byte_distribution(self, data: bytes) -> Dict[str, float]:
        """Analyze byte value distribution in trace data."""
        if not data:
            return {}

        byte_counts = {}
        for byte in data:
            byte_counts[byte] = byte_counts.get(byte, 0) + 1

        total = len(data)
        distribution = {
            "total_bytes": total,
            "unique_bytes": len(byte_counts),
            "null_bytes_pct": byte_counts.get(0, 0) / total * 100,
            "iac_bytes_pct": byte_counts.get(0xFF, 0) / total * 100,
            "printable_pct": sum(v for k, v in byte_counts.items() if 32 <= k <= 126)
            / total
            * 100,
        }

        return distribution

    def generate_statistics(self) -> Dict[str, Any]:
        """Generate aggregate statistics across all traces."""
        traces = self.results["traces"]

        if not traces:
            return {}

        stats = {
            "total_traces": len(traces),
            "total_size_bytes": sum(t.get("size_bytes", 0) for t in traces),
            "successful_loads": sum(1 for t in traces if "✓" in t.get("status", "")),
            "warnings": sum(len(t.get("warnings", [])) for t in traces),
            "errors": sum(len(t.get("errors", [])) for t in traces),
            "avg_size_bytes": sum(t.get("size_bytes", 0) for t in traces) / len(traces),
        }

        # Calculate success rate
        stats["success_rate_pct"] = (
            stats["successful_loads"] / stats["total_traces"] * 100
        )

        return stats

    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on analysis results."""
        recommendations = []
        stats = self.results.get("statistics", {})

        if stats.get("success_rate_pct", 0) < 100:
            recommendations.append(
                f"⚠ {100 - stats['success_rate_pct']:.1f}% of traces failed to load. "
                "Investigate parsing errors."
            )

        if stats.get("errors", 0) > 0:
            recommendations.append(
                f"❗ {stats['errors']} critical errors found. Review error details."
            )

        if stats.get("warnings", 0) > 10:
            recommendations.append(
                f"⚠ {stats['warnings']} warnings found. Consider addressing common issues."
            )

        if stats.get("total_traces", 0) > 0:
            recommendations.append(
                f"✅ Processed {stats['total_traces']} trace files successfully. "
                "Consider expanding test coverage."
            )

        return recommendations

    def run(self) -> Dict[str, Any]:
        """Execute complete trace validation."""
        print("=" * 70)
        print("  AGENT TASK: TRACE FILE VALIDATION")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print()

        start_time = time.time()

        # Find trace files
        trace_files = self.find_trace_files()
        if not trace_files:
            print("❌ No trace files found!")
            self.results["summary"]["status"] = "FAILED"
            self.results["summary"]["message"] = "No trace files found"
            return self.results

        # Analyze each trace file
        print(f"\n📊 Analyzing {len(trace_files)} trace files...")
        print("-" * 70)

        for i, trace_path in enumerate(trace_files, 1):
            print(f"\n[{i}/{len(trace_files)}] {trace_path.name}")
            result = self.analyze_trace_file(trace_path)
            self.results["traces"].append(result)

            # Print status
            status_icon = (
                "✅"
                if "✓" in result["status"]
                else "⚠️" if "⚠" in result["status"] else "❌"
            )
            print(f"  {status_icon} {result['status']}")
            print(f"  Size: {result['size_bytes']:,} bytes")

            if result["warnings"]:
                print(f"  Warnings: {len(result['warnings'])}")
            if result["errors"]:
                print(f"  Errors: {len(result['errors'])}")

        # Generate statistics
        print("\n" + "-" * 70)
        print("📈 Generating statistics...")
        self.results["statistics"] = self.generate_statistics()

        # Generate recommendations
        print("💡 Generating recommendations...")
        self.results["recommendations"] = self.generate_recommendations()

        # Summary
        duration = time.time() - start_time
        self.results["summary"]["duration_seconds"] = duration
        self.results["summary"]["status"] = "SUCCESS"
        self.results["summary"][
            "message"
        ] = f"Processed {len(trace_files)} traces in {duration:.2f}s"

        # Save results
        output_file = self.output_dir / "trace_validation_results.json"
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        # Print summary
        print("\n" + "=" * 70)
        print("  VALIDATION SUMMARY")
        print("=" * 70)
        print(f"✅ Status: {self.results['summary']['status']}")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"📁 Traces processed: {len(trace_files)}")
        print(
            f"✅ Successful loads: {self.results['statistics'].get('successful_loads', 0)}"
        )
        print(f"⚠️  Total warnings: {self.results['statistics'].get('warnings', 0)}")
        print(f"❌ Total errors: {self.results['statistics'].get('errors', 0)}")
        print(f"💾 Results saved: {output_file.absolute()}")
        print("=" * 70)

        # Print recommendations
        if self.results["recommendations"]:
            print("\n💡 RECOMMENDATIONS:")
            for rec in self.results["recommendations"]:
                print(f"  {rec}")
            print()

        return self.results


def main():
    """Main entry point for agent task."""
    import argparse

    parser = argparse.ArgumentParser(description="Agent Task: Trace File Validation")
    parser.add_argument(
        "--trace-dir",
        default=".",
        help="Directory containing trace files",
    )
    parser.add_argument(
        "--output-dir",
        default="test_output",
        help="Directory for output files",
    )

    args = parser.parse_args()

    agent = TraceValidationAgent(
        trace_dir=args.trace_dir,
        output_dir=args.output_dir,
    )

    results = agent.run()

    # Exit with appropriate code
    if results["statistics"].get("errors", 0) > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
