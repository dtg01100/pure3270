#!/usr/bin/env python3
"""
Quality Monitoring and Reporting System for Pure3270

This system provides comprehensive quality monitoring with:
1. Aggregated quality metrics from all quality tools
2. Quality trend analysis and historical tracking
3. Quality dashboard generation
4. Automated quality alerts and notifications
5. Quality report generation and distribution

Usage:
    python tools/quality_monitoring_system.py
    python tools/quality_monitoring_system.py --dashboard
    python tools/quality_monitoring_system.py --alerts
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


class QualityMonitoringSystem:
    """Comprehensive quality monitoring and reporting system."""

    def __init__(
        self,
        base_path: str = ".",
        quality_dir: str = "quality_reports",
        output_dir: str = "quality_reports",
    ):
        self.base_path = Path(base_path)
        self.quality_dir = Path(quality_dir)
        if output_dir != "quality_reports":
            self.quality_dir = Path(output_dir)
        self.quality_dir.mkdir(exist_ok=True)

        # Subdirectories for different quality reports
        self.reports_dir = self.quality_dir / "reports"
        self.trends_dir = self.quality_dir / "trends"
        self.dashboards_dir = self.quality_dir / "dashboards"
        self.alerts_dir = self.quality_dir / "alerts"

        for directory in [
            self.reports_dir,
            self.trends_dir,
            self.dashboards_dir,
            self.alerts_dir,
        ]:
            directory.mkdir(exist_ok=True)

        # Quality thresholds
        self.thresholds = {
            "dry_violations": {"high": 0, "medium": 3, "low": 5},
            "performance_regression": {"threshold": 1.5},  # 50% degradation
            "security_score": {"minimum": 80},
            "test_coverage": {"minimum": 80},
            "code_complexity": {"high": 15, "medium": 10},
        }

    def run_comprehensive_quality_scan(self) -> Dict[str, Any]:
        """Run all quality tools and aggregate results."""
        print("🔍 Running comprehensive quality scan...")
        print("=" * 60)

        # Initialize results container
        quality_results: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "base_path": str(self.base_path),
            "tools_executed": [],
            "results": {},
            "summary": {
                "overall_quality_score": 0,
                "quality_grade": "Unknown",
                "critical_issues": 0,
                "warnings": 0,
                "recommendations": [],
            },
        }

        # 1. Run DRY violation detection
        try:
            print("🔍 Running DRY violation detection...")
            dry_result = self._run_dry_detection()
            quality_results["results"]["dry_violations"] = dry_result
            quality_results["tools_executed"].append("dry_violation_detector")
        except Exception as e:
            print(f"❌ DRY detection failed: {e}")
            quality_results["results"]["dry_violations"] = {"error": str(e)}

        # 2. Run performance regression detection
        try:
            print("🔍 Running performance analysis...")
            perf_result = self._run_performance_analysis()
            quality_results["results"]["performance"] = perf_result
            quality_results["tools_executed"].append("performance_detector")
        except Exception as e:
            print(f"❌ Performance analysis failed: {e}")
            quality_results["results"]["performance"] = {"error": str(e)}

        # 3. Run security scanning
        try:
            print("🔍 Running security scanning...")
            security_result = self._run_security_scan()
            quality_results["results"]["security"] = security_result
            quality_results["tools_executed"].append("security_scanner")
        except Exception as e:
            print(f"❌ Security scan failed: {e}")
            quality_results["results"]["security"] = {"error": str(e)}

        # 4. Run code complexity analysis
        try:
            print("🔍 Running code complexity analysis...")
            complexity_result = self._run_complexity_analysis()
            quality_results["results"]["complexity"] = complexity_result
            quality_results["tools_executed"].append("complexity_analyzer")
        except Exception as e:
            print(f"❌ Complexity analysis failed: {e}")
            quality_results["results"]["complexity"] = {"error": str(e)}

        # 5. Run test coverage analysis
        try:
            print("🔍 Running test coverage analysis...")
            coverage_result = self._run_coverage_analysis()
            quality_results["results"]["coverage"] = coverage_result
            quality_results["tools_executed"].append("coverage_analyzer")
        except Exception as e:
            print(f"❌ Coverage analysis failed: {e}")
            quality_results["results"]["coverage"] = {"error": str(e)}

        # Calculate overall quality score
        quality_results["summary"] = self._calculate_quality_summary(
            quality_results["results"]
        )

        return quality_results

    def _run_dry_detection(self) -> Dict[str, Any]:
        """Run DRY violation detection tool."""
        try:
            result = subprocess.run(
                [sys.executable, "tools/dry_violation_detector.py", "--check-only"],
                cwd=self.base_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                return {"status": "clean", "violations": 0}
            else:
                return {"status": "violations_found", "error": result.stderr}

        except subprocess.TimeoutExpired:
            return {"status": "timeout"}
        except FileNotFoundError:
            return {"status": "not_found", "message": "DRY detector not available"}

    def _run_performance_analysis(self) -> Dict[str, Any]:
        """Run performance analysis."""
        try:
            # Create a simple performance baseline
            start_time = time.time()

            # Run a quick benchmark
            subprocess.run(
                [sys.executable, "quick_test.py"],
                cwd=self.base_path,
                capture_output=True,
                timeout=10,
            )

            end_time = time.time()
            duration = end_time - start_time

            return {
                "status": "completed",
                "quick_test_duration": duration,
                "performance_grade": (
                    "A" if duration < 1.0 else "B" if duration < 2.0 else "C"
                ),
                "regression_detected": duration > 2.0,
            }

        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "Performance test timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _run_security_scan(self) -> Dict[str, Any]:
        """Run security scanning."""
        try:
            result = subprocess.run(
                [sys.executable, "tools/enhanced_security_scanner.py", "--bandit-only"],
                cwd=self.base_path,
                capture_output=True,
                text=True,
                timeout=120,
            )

            return {
                "status": "completed",
                "bandit_result": result.returncode,
                "security_grade": "A" if result.returncode == 0 else "C",
            }

        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "Security scan timed out"}
        except FileNotFoundError:
            return {"status": "not_found", "message": "Security scanner not available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _run_complexity_analysis(self) -> Dict[str, Any]:
        """Run code complexity analysis."""
        try:
            result = subprocess.run(
                [sys.executable, "tools/code_analyzer.py", "--complexity-only"],
                cwd=self.base_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Parse output for complexity metrics
            if "High complexity functions" in result.stdout:
                # Extract number of high complexity functions
                lines = result.stdout.split("\n")
                for line in lines:
                    if "High complexity functions" in line:
                        count = int(line.split(":")[1].strip().split(" ")[0])
                        return {
                            "status": "completed",
                            "high_complexity_functions": count,
                            "complexity_grade": (
                                "A" if count == 0 else "B" if count < 5 else "C"
                            ),
                        }

            return {
                "status": "completed",
                "complexity_grade": "A",
                "message": "No high complexity functions detected",
            }

        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "Complexity analysis timed out"}
        except FileNotFoundError:
            return {"status": "not_found", "message": "Code analyzer not available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _run_coverage_analysis(self) -> Dict[str, Any]:
        """Run test coverage analysis."""
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "--cov=pure3270",
                    "--cov-report=json",
                    "--cov-report=term",
                ],
                cwd=self.base_path,
                capture_output=True,
                text=True,
                timeout=300,
            )

            # Look for coverage percentage in output
            if "TOTAL" in result.stdout:
                lines = result.stdout.split("\n")
                for line in lines:
                    if "TOTAL" in line and "%" in line:
                        # Extract coverage percentage
                        parts = line.split()
                        for part in parts:
                            if part.endswith("%"):
                                coverage = float(part[:-1])
                                return {
                                    "status": "completed",
                                    "coverage_percentage": coverage,
                                    "coverage_grade": (
                                        "A"
                                        if coverage >= 80
                                        else "B" if coverage >= 60 else "C"
                                    ),
                                }

            return {
                "status": "completed",
                "coverage_grade": "Unknown",
                "message": "Could not parse coverage results",
            }

        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "Coverage analysis timed out"}
        except FileNotFoundError:
            return {"status": "not_found", "message": "pytest-cov not available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _calculate_quality_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall quality summary."""
        summary = {
            "overall_quality_score": 0,
            "quality_grade": "Unknown",
            "critical_issues": 0,
            "warnings": 0,
            "recommendations": [],
        }

        scores = []
        critical_issues = []
        warnings = []
        recommendations = []

        # Analyze DRY violations
        dry_result = results.get("dry_violations", {})
        if dry_result.get("status") == "violations_found":
            critical_issues.append("DRY violations detected")
            recommendations.append("Refactor duplicated code blocks")

        # Analyze performance
        perf_result = results.get("performance", {})
        if perf_result.get("regression_detected"):
            warnings.append("Performance regression detected")
            recommendations.append("Optimize performance bottlenecks")

        # Analyze security
        security_result = results.get("security", {})
        if security_result.get("bandit_result", 0) != 0:
            critical_issues.append("Security issues detected")
            recommendations.append("Address security vulnerabilities")

        # Analyze complexity
        complexity_result = results.get("complexity", {})
        high_complexity = complexity_result.get("high_complexity_functions", 0)
        if high_complexity > 0:
            warnings.append(f"{high_complexity} high complexity functions detected")
            recommendations.append("Refactor complex functions")

        # Analyze coverage
        coverage_result = results.get("coverage", {})
        coverage = coverage_result.get("coverage_percentage", 0)
        if coverage < 80:
            recommendations.append(
                f"Increase test coverage to {80}% (currently {coverage:.1f}%)"
            )

        # Calculate overall score
        grade_scores = {"A": 90, "B": 80, "C": 70, "Unknown": 50}

        for result in [
            dry_result,
            perf_result,
            security_result,
            complexity_result,
            coverage_result,
        ]:
            grade = (
                result.get("dry_violations")
                or result.get("performance_grade")
                or result.get("security_grade")
                or result.get("complexity_grade")
                or result.get("coverage_grade")
            )
            if grade in grade_scores:
                scores.append(grade_scores[grade])

        if scores:
            summary["overall_quality_score"] = sum(scores) / len(scores)

            # Determine overall grade
            avg_score = float(summary["overall_quality_score"])  # type: ignore
            if avg_score >= 90:
                summary["quality_grade"] = "A+"  # type: ignore
            elif avg_score >= 85:
                summary["quality_grade"] = "A"  # type: ignore
            elif avg_score >= 80:
                summary["quality_grade"] = "B"  # type: ignore
            elif avg_score >= 70:
                summary["quality_grade"] = "C"  # type: ignore
            else:
                summary["quality_grade"] = "D"  # type: ignore

        summary["critical_issues"] = len(critical_issues)
        summary["warnings"] = len(warnings)
        summary["recommendations"] = recommendations

        return summary

    def save_quality_report(self, results: Dict[str, Any]) -> str:
        """Save quality report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / f"quality_report_{timestamp}.json"

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        return str(report_file)

    def generate_quality_dashboard(self, results: Dict[str, Any]) -> str:
        """Generate HTML quality dashboard."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dashboard_file = self.dashboards_dir / f"quality_dashboard_{timestamp}.html"

        # Generate HTML dashboard
        html_content = self._create_dashboard_html(results)

        with open(dashboard_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return str(dashboard_file)

    def _create_dashboard_html(self, results: Dict[str, Any]) -> str:
        """Create HTML dashboard content."""
        summary = results.get("summary", {})
        overall_score = summary.get("overall_quality_score", 0)
        quality_grade = summary.get("quality_grade", "Unknown")
        critical_issues = summary.get("critical_issues", 0)
        warnings = summary.get("warnings", 0)
        recommendations = summary.get("recommendations", [])

        # Color coding for grades
        grade_color = {
            "A+": "#28a745",
            "A": "#20c997",
            "B": "#17a2b8",
            "C": "#ffc107",
            "D": "#fd7e14",
            "F": "#dc3545",
            "Unknown": "#6c757d",
        }.get(quality_grade, "#6c757d")

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pure3270 Quality Dashboard</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .metric-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric-title {{ font-size: 14px; color: #666; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }}
        .metric-value {{ font-size: 32px; font-weight: bold; color: #333; }}
        .grade-circle {{ width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold; color: white; background-color: {grade_color}; margin: 0 auto; }}
        .section {{ background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .section h3 {{ margin-top: 0; color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        .tool-status {{ display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #eee; }}
        .status-badge {{ padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; text-transform: uppercase; }}
        .status-pass {{ background-color: #d4edda; color: #155724; }}
        .status-warn {{ background-color: #fff3cd; color: #856404; }}
        .status-fail {{ background-color: #f8d7da; color: #721c24; }}
        .recommendations {{ list-style: none; padding: 0; }}
        .recommendations li {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
        .recommendations li:before {{ content: "💡 "; margin-right: 8px; }}
        .timestamp {{ text-align: center; color: #666; font-size: 14px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ Pure3270 Quality Dashboard</h1>
            <p>Comprehensive Quality Assessment Report</p>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-title">Overall Quality Score</div>
                <div class="metric-value">{overall_score:.1f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Quality Grade</div>
                <div class="grade-circle">{quality_grade}</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Critical Issues</div>
                <div class="metric-value" style="color: {'#dc3545' if critical_issues > 0 else '#28a745'};">{critical_issues}</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Warnings</div>
                <div class="metric-value" style="color: {'#ffc107' if warnings > 0 else '#28a745'};">{warnings}</div>
            </div>
        </div>

        <div class="section">
            <h3>🔍 Quality Tool Results</h3>
        """

        # Add tool status
        tools = results.get("results", {})
        for tool_name, tool_result in tools.items():
            status = tool_result.get("status", "unknown")
            if status == "completed" or status == "clean":
                status_class = "status-pass"
                status_text = "PASS"
            elif status == "timeout" or "error" in status:
                status_class = "status-fail"
                status_text = "FAIL"
            else:
                status_class = "status-warn"
                status_text = "WARN"

            tool_display_name = tool_name.replace("_", " ").title()
            html += f"""
            <div class="tool-status">
                <span>{tool_display_name}</span>
                <span class="status-badge {status_class}">{status_text}</span>
            </div>
            """

        html += """
        </div>

        <div class="section">
            <h3>📋 Recommendations</h3>
        """

        if recommendations:
            html += "<ul class='recommendations'>"
            for rec in recommendations:
                html += f"<li>{rec}</li>"
            html += "</ul>"
        else:
            html += "<p style='color: #28a745; font-weight: bold;'>✅ No recommendations - excellent quality!</p>"

        html += f"""
        </div>

        <div class="timestamp">
            Report generated: {results.get('timestamp', 'Unknown timestamp')}
        </div>
    </div>
</body>
</html>
        """

        return html

    def check_quality_alerts(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for quality alerts based on thresholds."""
        alerts = []
        summary = results.get("summary", {})

        # Check critical issues
        if summary.get("critical_issues", 0) > 0:
            alerts.append(
                {
                    "type": "critical",
                    "message": f"Critical quality issues detected: {summary['critical_issues']}",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "recommendation": "Address critical issues immediately",
                }
            )

        # Check quality score
        score = summary.get("overall_quality_score", 0)
        if score < 70:
            alerts.append(
                {
                    "type": "warning",
                    "message": f"Quality score below threshold: {score:.1f}%",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "recommendation": "Review and improve code quality",
                }
            )

        # Check specific tool failures
        results_data = results.get("results", {})
        for tool_name, tool_result in results_data.items():
            status = tool_result.get("status", "")
            if "error" in status or status == "timeout":
                alerts.append(
                    {
                        "type": "tool_failure",
                        "message": f"Quality tool failed: {tool_name}",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "recommendation": "Check tool configuration and dependencies",
                    }
                )

        return alerts

    def save_alerts(self, alerts: List[Dict[str, Any]]) -> Optional[str]:
        """Save alerts to file."""
        if not alerts:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        alert_file = self.alerts_dir / f"quality_alerts_{timestamp}.json"

        alert_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "alert_count": len(alerts),
            "alerts": alerts,
        }

        with open(alert_file, "w", encoding="utf-8") as f:
            json.dump(alert_data, f, indent=2)

        return str(alert_file)

    def print_quality_summary(self, results: Dict[str, Any]) -> None:
        """Print quality summary to console."""
        print("\n" + "=" * 60)
        print("📊 QUALITY MONITORING SUMMARY")
        print("=" * 60)

        summary = results.get("summary", {})
        tools_executed = results.get("tools_executed", [])

        print(f"🕒 Timestamp: {results.get('timestamp', 'Unknown')}")
        print(f"🔧 Tools Executed: {len(tools_executed)}")
        print(
            f"📈 Overall Quality Score: {summary.get('overall_quality_score', 0):.1f}%"
        )
        print(f"🏆 Quality Grade: {summary.get('quality_grade', 'Unknown')}")
        print(f"🚨 Critical Issues: {summary.get('critical_issues', 0)}")
        print(f"⚠️ Warnings: {summary.get('warnings', 0)}")

        # Tool results
        print(f"\n🔍 Tool Results:")
        for tool in tools_executed:
            result = results.get("results", {}).get(tool, {})
            status = result.get("status", "unknown")
            status_emoji = (
                "✅"
                if status in ["completed", "clean"]
                else "❌" if "error" in status or status == "timeout" else "⚠️"
            )
            print(f"  {status_emoji} {tool}: {status}")

        # Recommendations
        recommendations = summary.get("recommendations", [])
        if recommendations:
            print(f"\n💡 Recommendations ({len(recommendations)}):")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        else:
            print(f"\n✅ No recommendations - excellent quality!")


def main():
    parser = argparse.ArgumentParser(
        description="Quality Monitoring and Reporting System for Pure3270"
    )
    parser.add_argument(
        "--scan", action="store_true", help="Run comprehensive quality scan"
    )
    parser.add_argument(
        "--dashboard", action="store_true", help="Generate quality dashboard"
    )
    parser.add_argument(
        "--alerts", action="store_true", help="Check for quality alerts"
    )
    parser.add_argument(
        "--output-dir", default="quality_reports", help="Output directory for reports"
    )
    parser.add_argument("--save-report", help="Save report to specific file")

    args = parser.parse_args()

    # Default to scan if no specific action requested
    if not any([args.scan, args.dashboard, args.alerts]):
        args.scan = True

    monitor = QualityMonitoringSystem(output_dir=args.output_dir)

    # Run quality scan
    if args.scan:
        print("🔍 Starting comprehensive quality monitoring...")
        results = monitor.run_comprehensive_quality_scan()

        # Save report
        if args.save_report:
            report_file = monitor.save_quality_report(results)
        else:
            report_file = monitor.save_quality_report(results)
        print(f"📄 Quality report saved to: {report_file}")

        # Generate dashboard
        if args.dashboard:
            dashboard_file = monitor.generate_quality_dashboard(results)
            print(f"📊 Quality dashboard saved to: {dashboard_file}")

        # Check alerts
        if args.alerts:
            alerts = monitor.check_quality_alerts(results)
            if alerts:
                alert_file = monitor.save_alerts(alerts)
                if alert_file:
                    print(f"🚨 Quality alerts saved to: {alert_file}")
            else:
                print("✅ No quality alerts detected")

        # Print summary
        monitor.print_quality_summary(results)

        # Return appropriate exit code
        summary = results.get("summary", {})
        if summary.get("critical_issues", 0) > 0:
            return 1
        elif summary.get("overall_quality_score", 0) < 70:
            return 1

    return 0


if __name__ == "__main__":
    exit(main())
