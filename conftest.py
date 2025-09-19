import asyncio
import sys
import pytest

# Removed broken fixtures that reference non-existent TN3270ENegotiatingMockServer

# Python 3.9 compatibility: Ensure event loop is available for async tests
if sys.version_info < (3, 10):
    @pytest.fixture(scope="function")
    def event_loop():
        """Create an instance of the default event loop for the test function."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        yield loop
        loop.close()
        asyncio.set_event_loop(None)
