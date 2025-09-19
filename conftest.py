import asyncio
import sys
import pytest

# Removed broken fixtures that reference non-existent TN3270ENegotiatingMockServer

# We now require Python >= 3.10; pytest-asyncio provides proper event loop handling
# so the manual event_loop fixture for older Python versions is no longer necessary.
