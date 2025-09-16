import platform
import resource

from tools.memory_limit import set_memory_limit

# Set memory limit for the script
set_memory_limit(500)


def set_memory_limit(max_memory_mb: int):
    """
    Set maximum memory limit for the current process.

    Args:
        max_memory_mb: Maximum memory in megabytes
    """
    # Only works on Unix systems
    if platform.system() != "Linux":
        return None

    try:
        max_memory_bytes = max_memory_mb * 1024 * 1024
        # RLIMIT_AS limits total virtual memory
        resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))
        return max_memory_bytes
    except Exception:
        return None


#!/usr/bin/env python3
"""
Simple test script focusing on mock server functionality only.
"""

import asyncio
import os
import sys

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
