import asyncio
import sys
import pytest

# Removed broken fixtures that reference non-existent TN3270ENegotiatingMockServer

# Python 3.9 compatibility: Ensure event loop is available for async tests
if sys.version_info < (3, 10):
    @pytest.fixture(scope="session")
    def event_loop():
        """Create an instance of the default event loop for the test session."""
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
        loop.close()
