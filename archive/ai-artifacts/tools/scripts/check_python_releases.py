#!/usr/bin/env python3
"""
Script to check for new Python releases and output in JSON format.
"""

import json
import sys
from xml.etree import ElementTree as ET

import requests


def check_python_releases():
    """Check for new Python releases from python.org RSS."""
    try:
        # Fetch Python releases RSS
        response = requests.get("https://www.python.org/downloads/versions/rss/")
        response.raise_for_status()

        # Parse RSS
        root = ET.fromstring(response.content)
        items = root.findall(".//item")

        # Find latest stable Python 3.x.y (non-alpha/beta/rc)
        latest = "3.13.0"  # Default
        for item in items:
            title_elem = item.find("title")
            if title_elem is not None:
                title = title_elem.text
                if title and "Python " in title and "release" in title.lower():
                    # Extract version from title like "Python 3.13.0 (Oct. 7, 2024)"
                    ver_str = title.split("Python ")[1].split(" ")[0]
                    if ver_str.startswith("3.") and not any(
                        s in ver_str for s in ["a", "b", "rc"]
                    ):
                        if version.parse(ver_str) > version.parse(latest):
                            latest = ver_str

        output = {"latest_minor": latest}
        print(json.dumps(output))
        return output
    except Exception as e:
        print(json.dumps({"error": str(e), "latest_minor": "3.13.0"}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    check_python
