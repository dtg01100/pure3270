#!/usr/bin/env python3
import json
import os

try:
    import defusedxml.ElementTree as ET
except ImportError:
    # Fallback with warning - defusedxml not available
    import warnings
    import xml.etree.ElementTree as ET  # nosec B405

    warnings.warn(
        "defusedxml not available - using potentially unsafe XML parser. "
        "Install defusedxml for better security: pip install defusedxml",
        UserWarning,
    )
from argparse import ArgumentParser

from openai import OpenAI


def parse_pytest_xml(xml_file):
    """Parse pytest XML report."""
    tree = ET.parse(xml_file)  # nosec B314
    root = tree.getroot()
    failures = []
    for testcase in root.findall(".//testcase"):
        failure = testcase.find("failure")
        if failure is not None:
            failures.append(
                {
                    "name": testcase.get("name"),
                    "message": failure.get("message", ""),
                    "traceback": failure.text or "",
                }
            )
    return failures


def analyze_with_ai(failures, api_key):
    """Analyze failures with OpenAI."""
    client = OpenAI(api_key=api_key)

    prompt = f"""
    Analyze these test failures from pure3270 project:

    {json.dumps(failures, indent=2)}

    Provide:
    1. Summary of failure patterns
    2. Likely root causes
    3. Suggested fixes for each failure
    4. Priority ranking
    5. Regression risk assessment

    Focus on protocol, emulation, or compatibility issues.
    """

    response = client.chat.completions.create(
        model="gpt-4", messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


def main():
    parser = ArgumentParser()
    parser.add_argument("--test-xml", required=True, help="Pytest XML report")
    parser.add_argument("--coverage-xml", help="Coverage XML report")
    parser.add_argument("--output", default="regression_analysis.json")
    args = parser.parse_args()

    failures = parse_pytest_xml(args.test_xml)

    if not failures:
        print("No test failures found.")
        return

    if "OPENAI_API_KEY" in os.environ:
        analysis = analyze_with_ai(failures, os.environ["OPENAI_API_KEY"])
        result = {"failures": failures, "ai_analysis": analysis}
    else:
        result = {"failures": failures, "analysis": "AI analysis skipped - no API key"}

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Analysis saved to {args.output}")


if __name__ == "__main__":
    main()
