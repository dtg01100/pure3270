#!/usr/bin/env python3
"""
API compatibility reporting script for pure3270.P3270Client.

Generates reports on compatibility with p3270.P3270Client API.
"""

import sys
from pathlib import Path

# Add pure3270 to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_api_compatibility import APICompatibilityTest


def main() -> int:
    """Generate API compatibility report."""
    print("Generating P3270Client API compatibility report...")

    tester = APICompatibilityTest()
    success = tester.run_all_tests()

    # Save detailed report
    report = tester.generate_report()
    report_file = Path("api_compatibility_report.md")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✓ Report saved to {report_file}")

    # Print summary
    present = len(tester.results["present_methods"])
    expected = len(tester.results["present_methods"]) + len(
        tester.results["missing_methods"]
    )
    compatibility_pct = (present / expected * 100) if expected > 0 else 0

    print(".1f")
    if success:
        print("🎉 Full API compatibility achieved!")
        return 0
    else:
        print("⚠️  Some compatibility issues found")
        return 1


if __name__ == "__main__":
    sys.exit(main())
