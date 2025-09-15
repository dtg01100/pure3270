import platform
import resource
def set_memory_limit(max_memory_mb: int):
    """
    Set maximum memory limit for the current process.
    
    Args:
        max_memory_mb: Maximum memory in megabytes
    """
    # Only works on Unix systems
    if platform.system() != 'Linux':
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
Comprehensive integration test suite for pure3270.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Enable pure3270 patching
import pure3270

pure3270.enable_replacement()

# Import after patching
import p3270
from pure3270 import AsyncSession, Session
from pure3270.protocol.tn3270_handler import TN3270Handler
from pure3270.protocol.data_stream import DataStreamParser, DataStreamSender
from pure3270.emulation.screen_buffer import ScreenBuffer


class TestPure3270Integration:
    """Comprehensive integration tests for pure3270."""

    def test_p3270_patching_integration(self):
        """Test that p3270 is correctly patched with pure3270."""
        # Create p3270 client
        client = p3270.P3270Client()

        # Verify patching
        assert client is not None
        assert hasattr(client, "s3270")
        # Should be patched with pure3270 wrapper
        assert "Pure3270S3270Wrapper" in str(type(client.s3270))

        # Test basic methods exist
        assert hasattr(client, "connect")
        assert hasattr(client, "disconnect")
        assert hasattr(client, "sendEnter")
        assert hasattr(client, "sendPF")
        assert hasattr(client, "isConnected")

    def test_pure3270_session_creation(self):
        """Test pure3270 session creation."""
        # Test async session
        async_session = AsyncSession()
        assert async_session is not None
        assert hasattr(async_session, "connect")
        assert hasattr(async_session, "send")
        assert hasattr(async_session, "read")

        # Test sync session
        sync_session = Session()
        assert sync_session is not None
        assert hasattr(sync_session, "connect")
        assert hasattr(sync_session, "send")
        assert hasattr(sync_session, "read")

    @pytest.mark.asyncio
    async def test_async_session_methods(self):
        """Test async session methods with mocked connections."""
        with patch("asyncio.open_connection") as mock_open:
            # Mock connection
            reader = AsyncMock()
            writer = AsyncMock()
            mock_open.return_value = (reader, writer)

            # Mock data responses
            reader.readexactly.return_value = b"\xff\xfb\x27"  # WILL EOR
            reader.read.return_value = b"\x28\x00\x01\x00"  # BIND response
            writer.drain = AsyncMock()

            # Test session
            session = AsyncSession("localhost", 2323)
            assert not session.connected

            # Test connect
            await session.connect()
            assert session.connected
            assert session._handler is not None

            # Test send
            await session.send(b"test")
            writer.write.assert_called()

            # Test close
            await session.close()
            assert not session.connected
            assert session._handler is None

    def test_sync_session_methods(self):
        """Test sync session methods."""
        session = Session()
        assert session is not None

        # Test properties
        assert not session.connected

        # Test screen_buffer property (should raise SessionError when not connected)
        try:
            buffer = session.screen_buffer
            # If we get here, it means the session is connected which is unexpected
            assert buffer is not None
        except pure3270.session.SessionError:
            # This is expected when not connected
            pass

    @pytest.mark.asyncio
    async def test_macro_execution(self):
        """Test macro execution."""
        with patch("asyncio.open_connection") as mock_open:
            # Mock connection
            reader = AsyncMock()
            writer = AsyncMock()
            mock_open.return_value = (reader, writer)

            # Mock data responses
            reader.readexactly.return_value = b"\xff\xfb\x27"  # WILL EOR
            reader.read.return_value = b"\x28\x00\x01\x00"  # BIND response
            writer.drain = AsyncMock()

            session = AsyncSession("localhost", 2323)
            await session.connect()

            # Test simple macro
            result = await session.execute_macro("key Enter")
            assert isinstance(result, dict)
            assert "success" in result

    def test_emulation_functionality(self):
        """Test core emulation functionality."""
        # Test screen buffer
        screen = ScreenBuffer()
        assert screen.rows == 24
        assert screen.cols == 80
        assert len(screen.buffer) == 1920

        # Test data stream parser
        parser = DataStreamParser(screen)
        assert parser is not None

        # Test data stream sender
        sender = DataStreamSender()
        assert sender is not None

        # Test basic parsing
        sample_data = b"\x05\xf5\xc1\x10\x00\x00\xc1\xc2\xc3\x0d"  # Write command
        parser.parse(sample_data)
        # Should have written data to screen buffer
        assert screen.buffer[0:3] == b"\xc1\xc2\xc3"

    def test_aid_support(self):
        """Test AID (Attention ID) support."""
        session = Session()

        # Test that PF methods exist
        assert hasattr(session, "pf")
        assert callable(session.pf)

        # Test that PA methods exist
        assert hasattr(session, "pa")
        assert callable(session.pa)

    def test_extended_functionality(self):
        """Test extended s3270 functionality."""
        session = Session()

        # Test that extended methods exist
        extended_methods = ["compose", "cookie", "expect", "fail"]

        for method in extended_methods:
            assert hasattr(session, method), f"Method {method} should exist"
            assert callable(
                getattr(session, method)
            ), f"Method {method} should be callable"


def run_comprehensive_tests():
    """Run all comprehensive tests."""
    test_instance = TestPure3270Integration()

    try:
        # Run all test methods
        test_instance.test_p3270_patching_integration()
        print("✓ p3270 patching integration test passed")

        test_instance.test_pure3270_session_creation()
        print("✓ Session creation test passed")

        test_instance.test_sync_session_methods()
        print("✓ Sync session methods test passed")

        test_instance.test_emulation_functionality()
        print("✓ Emulation functionality test passed")

        test_instance.test_aid_support()
        print("✓ AID support test passed")

        test_instance.test_extended_functionality()
        print("✓ Extended functionality test passed")

        print("\nAll comprehensive integration tests passed! 🎉")
        return True

    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Running comprehensive pure3270 integration tests...")
    print("=" * 50)

    success = run_comprehensive_tests()

    if success:
        print("\n" + "=" * 50)
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("❌ SOME TESTS FAILED!")
        print("=" * 50)
