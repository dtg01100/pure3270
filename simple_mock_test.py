#!/usr/bin/env python3
"""
Simple test script focusing on mock server functionality only.
"""

import asyncio
import sys
import os

# Add the current directory to the path so we can import pure3270
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from integration_test import test_with_mock_server


async def main():
    """Run the mock server test."""
    print("Running simple mock server test...")
    try:
        result = await test_with_mock_server()
        print(f"Test result: {'PASSED' if result else 'FAILED'}")
        return 0 if result else 1
    except Exception as e:
        print(f"Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
