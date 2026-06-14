import asyncio
import platform
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.exceptions import NotConnectedError
from pure3270.protocol.data_stream import DataStreamParser
from pure3270.protocol.exceptions import NegotiationError, ProtocolError
from pure3270.protocol.negotiator import Negotiator
from pure3270.protocol.utils import (
    IAC,
    SB,
    SE,
    TELOPT_TN3270E,
    TN3270E_BIND_IMAGE,
    TN3270E_DATA_STREAM_CTL,
    TN3270E_DEVICE_TYPE,
    TN3270E_FUNCTIONS,
    TN3270E_IBM_DYNAMIC,
    TN3270E_IS,
    TN3270E_REQUEST,
    TN3270E_RESPONSES,
    TN3270E_SCS_CTL_CODES,
    TN3270E_SEND,
    TN3270E_SYSREQ,
)


@pytest.mark.skipif(
    platform.system() != "Linux", reason="Memory limiting only supported on Linux"
)
class TestNegotiatorMissingCoverage:
    """Tests for missing coverage in negotiator.py"""

    @pytest.fixture
    def negotiator(self, memory_limit_500mb):
        parser = DataStreamParser(ScreenBuffer())
        screen_buffer = ScreenBuffer()
        return Negotiator(None, parser, screen_buffer)

    @pytest.mark.asyncio
    async def test_parse_tn3270e_subnegotiation_edge_cases(
        self, negotiator, memory_limit_500mb
    ):
        """Test edge cases in TN3270E subnegotiation parsing."""
        # Test with malformed data that should be handled gracefully
        with patch.object(
            negotiator, "_handle_tn3270e_response", return_value=None
        ) as mock_handle:
            await negotiator._parse_tn3270e_subnegotiation(b"")
            mock_handle.assert_not_called()

        with patch.object(
            negotiator, "_handle_tn3270e_response", return_value=None
        ) as mock_handle:
            await negotiator._parse_tn3270e_subnegotiation(b"\x00")
            mock_handle.assert_not_called()

        with patch.object(
            negotiator, "_handle_tn3270e_response", return_value=None
        ) as mock_handle:
            await negotiator._parse_tn3270e_subnegotiation(b"\xff\xff\xff")
            mock_handle.assert_not_called()

        # Test with invalid TN3270E option
        await negotiator._parse_tn3270e_subnegotiation(
            b"\x99\x01\x02"
        )  # Invalid option 0x99

    @pytest.mark.asyncio
    async def test_handle_device_type_subnegotiation_invalid_data(
        self, negotiator, memory_limit_500mb
    ):
        """Test handling of invalid device type subnegotiation data."""
        # Test with data that doesn't match expected format
        await negotiator._handle_tn3270e_is(b"")
        await negotiator._handle_tn3270e_is(b"\x01")  # Missing sub-type
        await negotiator._handle_tn3270e_is(b"\x03\x01")  # REJECT with no reason

    @pytest.mark.asyncio
    async def test_handle_functions_subnegotiation_invalid_data(
        self, negotiator, memory_limit_500mb
    ):
        """Test handling of invalid functions subnegotiation data."""
        # Test with malformed function data
        await negotiator._handle_tn3270e_is(b"")
        await negotiator._handle_tn3270e_is(b"\x01")  # Missing function bits
        await negotiator._handle_tn3270e_is(b"\x99\x01\x02")  # Invalid sub-type

    @pytest.mark.asyncio
    async def test_send_supported_device_types_no_writer(
        self, negotiator, memory_limit_500mb
    ):
        """Test sending device types when writer is None."""
        # This should log an error but not crash
        await negotiator._send_supported_device_types()

    @pytest.mark.asyncio
    async def test_send_supported_functions_no_writer(
        self, negotiator, memory_limit_500mb
    ):
        """Test sending functions when writer is None."""
        # This should log an error but not crash
        await negotiator._send_functions_is()

    @pytest.mark.asyncio
    async def test_lu_name_property(self, negotiator, memory_limit_500mb):
        """Test LU name property getter and setter."""
        # Test getter when None
        assert negotiator.lu_name is None

        # Test setter and getter
        negotiator.lu_name = "TEST-LU"
        assert negotiator.lu_name == "TEST-LU"

        # Test setting to None
        negotiator.lu_name = None
        assert negotiator.lu_name is None

    @pytest.mark.asyncio
    async def test_is_printer_session_active(self, negotiator, memory_limit_500mb):
        """Test printer session detection."""
        # Initially should be False
        assert negotiator.is_printer_session_active() is False

        # Set printer session flag
        negotiator.is_printer_session = True
        assert negotiator.is_printer_session_active() is True

    @pytest.mark.asyncio
    async def test_receive_data_no_handler(self, negotiator, memory_limit_500mb):
        """Test receiving data when no handler is available."""
        with pytest.raises(NotImplementedError):
            await negotiator._receive_data()

    @pytest.mark.asyncio
    async def test_read_iac_no_handler(self, negotiator, memory_limit_500mb):
        """Test reading IAC when no handler is available."""
        with pytest.raises(NotImplementedError):
            await negotiator._read_iac()

    @pytest.mark.asyncio
    async def test_negotiate_no_writer(self, negotiator, memory_limit_500mb):
        """Test negotiate when writer is None."""
        negotiator.writer = None
        with pytest.raises(NotConnectedError):
            await negotiator.negotiate()

    @pytest.mark.asyncio
    async def test_handle_device_type_is_with_invalid_data(
        self, negotiator, memory_limit_500mb
    ):
        """Test DEVICE-TYPE IS handling with invalid device type data."""
        # Test with malformed device type string
        await negotiator._handle_tn3270e_is(b"")
        await negotiator._handle_tn3270e_is(b"incomplete\x00")

    @pytest.mark.asyncio
    async def test_handle_device_type_request_with_no_supported_types(
        self, negotiator, memory_limit_500mb
    ):
        """Test DEVICE-TYPE REQUEST handling when no supported types."""
        # Clear supported types
        negotiator.supported_device_types = []
        await negotiator._send_supported_device_types()

    @pytest.mark.asyncio
    async def test_handle_functions_is_with_empty_data(
        self, negotiator, memory_limit_500mb
    ):
        """Test FUNCTIONS IS handling with empty function data."""
        await negotiator._handle_tn3270e_is(b"")

    @pytest.mark.asyncio
    async def test_handle_functions_request_with_no_supported_functions(
        self, negotiator, memory_limit_500mb
    ):
        """Test FUNCTIONS REQUEST handling when no supported functions."""
        # Clear supported functions
        negotiator.supported_functions = 0
        await negotiator._handle_tn3270e_send(TN3270E_FUNCTIONS)

    @pytest.mark.asyncio
    async def test_send_supported_device_types_with_empty_supported_list(
        self, negotiator, memory_limit_500mb
    ):
        """Test sending device types when supported list is empty."""
        negotiator.writer = MagicMock()
        negotiator.supported_device_types = []
        await negotiator._send_supported_device_types()

    @pytest.mark.asyncio
    async def test_send_supported_functions_with_no_functions(
        self, negotiator, memory_limit_500mb
    ):
        """Test sending functions when no functions are supported."""
        negotiator.writer = AsyncMock()
        negotiator.supported_functions = 0
        await negotiator._send_functions_is()

    @pytest.mark.asyncio
    async def test_default_functions_bytes_match_s3270_trace(
        self, negotiator, memory_limit_500mb
    ):
        """Verify default FUNCTIONS REQUEST/IS bytes match s3270 traces.

        The default FUNCTIONS payload (when no negotiation has occurred)
        must match what s3270 actually sends, per
        ``tests/data/traces/bid.trc`` and ``ibmlink2.trc``:

        .. code-block:: text

            fffa 28 03 07 00 02 04 05 fff0    (REQUEST)
            fffa 28 03 04 00 02 04 05 fff0    (IS)

        The 4-byte function mask is ``0x00 0x02 0x04 0x05`` (== int
        ``0x00020405``), which encodes BIND-IMAGE, RESPONSES, SYSREQ,
        and CONTENTION-RESOLUTION per RFC 2355.
        """
        expected = bytes([0x00, 0x02, 0x04, 0x05])
        for command in (TN3270E_REQUEST, TN3270E_IS):
            # Use AsyncMock so the writer's ``drain()`` coroutine works
            # when ``_send_functions_request/is`` awaits it.
            writer = MagicMock()
            writer.drain = AsyncMock()
            writer.wait_closed = AsyncMock()
            negotiator.writer = writer
            # Force the fallback branch by clearing cached functions.
            if hasattr(negotiator, "_functions"):
                negotiator._functions = None
            if command == TN3270E_REQUEST:
                await negotiator._send_functions_request()
            else:
                await negotiator._send_functions_is()
            # Find the most recent subnegotiation call with the
            # expected TN3270E/FUNCTIONS prefix.
            sent_payloads = [call.args[0] for call in writer.write.call_args_list]
            found = False
            for payload in sent_payloads:
                # + IAC SE by ``send_subnegotiation``. Strip the trailer
                # before extracting the FUNCTIONS payload.
                payload = bytes(payload)
                if not (
                    len(payload) >= 5
                    and payload[0] == IAC
                    and payload[1] == SB
                    and payload[2] == TELOPT_TN3270E
                    and payload[3] == TN3270E_FUNCTIONS
                    and payload[4] == command
                ):
                    continue
                function_bytes = payload[5:-2]  # drop IAC SE
                assert function_bytes == expected, (
                    f"Default FUNCTIONS payload {function_bytes.hex()} "
                    f"does not match s3270 trace {expected.hex()}"
                )
                found = True
                break
            assert found, (
                f"No FUNCTIONS subnegotiation with command {command:#x} "
                f"was sent. Calls: {writer.write.call_args_list}"
            )
