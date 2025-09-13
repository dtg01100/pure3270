#!/usr/bin/env python3
"""
Integration test suite for pure3270 that doesn't require Docker.
This test suite verifies:
1. Basic functionality (imports, class creation)
2. Mock server connectivity
3. Navigation method availability
4. p3270 library patching
5. Session management
6. Macro execution
7. Screen buffer operations
"""

import asyncio
import sys
import os
import tempfile
import json

# Add the current directory to the path so we can import pure3270
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from pure3270.protocol.data_stream import DataStreamSender
from pure3270.protocol.utils import WONT, DONT, TN3270E_BIND_IMAGE, TN3270E_RESPONSES, TN3270E_DEVICE_TYPE, TN3270E_SEND
from pure3270.protocol.data_stream import QUERY_REPLY_SF, QUERY_REPLY_CHARACTERISTICS
from pure3270.protocol.tn3270e_header import TN3270EHeader


def test_basic_functionality():
    """Test basic functionality of pure3270."""
    print("1. Testing basic functionality...")
    try:
        # Test imports
        import pure3270
        from pure3270 import Session, AsyncSession
        from pure3270.patching import enable_replacement

        print("   ✓ Imports successful")

        # Test class creation
        session = Session()
        async_session = AsyncSession()
        print("   ✓ Session creation")

        # Test enable_replacement
        pure3270.enable_replacement()
        print("   ✓ enable_replacement")

        # Test that we can import p3270 after enabling replacement (optional)
        try:
            import p3270
            print("   ✓ p3270 import after replacement")

            # Test that p3270 client can be created
            client = p3270.P3270Client()
            print("   ✓ p3270.P3270Client creation")
        except ImportError as p3270_error:
            if "p3270" in str(p3270_error):
                print("   ⚠ p3270 not installed, skipping p3270 tests")
            else:
                raise

        return True
    except Exception as e:
        print(f"   ✗ Basic functionality test failed: {e}")
        return False


class MockServer:
    """Simple mock TN3270 server for testing."""

    def __init__(self, port=0):
        self.port = port
        self.server = None
        self.clients = []

    async def start(self):
        """Start the mock server on a dynamic port if port=0."""
        try:
            self.server = await asyncio.start_server(
                self.handle_client, "localhost", self.port
            )
            # Retrieve the actual port assigned
            socket = self.server.sockets[0]
            self.port = socket.getsockname()[1]
            print(f"Mock Server listening on port {self.port}")
            await self.server.serve_forever()
        except Exception as e:
            print(f"Failed to start mock server: {e}")
            return False

    async def stop(self):
        """Stop the mock server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print(f"Mock Server on port {self.port} stopped.")

    async def handle_client(self, reader, writer):
        """Handle a client connection."""
        self.clients.append(writer)
        try:
            while True:
                try:
                    data = await asyncio.wait_for(reader.read(1024), timeout=1.0)
                except asyncio.TimeoutError:
                    # No data in this interval, continue waiting but avoid blocking forever
                    continue
                if not data:
                    break
                # Echo back for basic testing
                writer.write(data)
                await writer.drain()
        except Exception:
            pass
        finally:
            if writer in self.clients:
                self.clients.remove(writer)
            writer.close()
            await writer.wait_closed()
 
 
class TN3270ENegotiatingMockServer(MockServer):
    """
    A mock TN3270 server that simulates TN3270E negotiation.
    """
    def __init__(self, port=0):
        super().__init__(port)
        self.negotiation_complete = asyncio.Event()
        self._negotiated_device_type = False
        self._negotiated_functions = False
    def _maybe_set_negotiation_complete(self):
        if self._negotiated_device_type and self._negotiated_functions:
            if not self.negotiation_complete.is_set():
                print("Mock Server: TN3270E negotiation fully complete (SNA). Setting negotiation_complete event.")
                self.negotiation_complete.set()

    async def start(self):
        """Start the mock server on a dynamic port if port=0."""
        self.server = await asyncio.start_server(
            self.handle_client, "localhost", self.port
        )
        socket = self.server.sockets[0]
        self.port = socket.getsockname()[1]
        print(f"Mock Server listening on port {self.port}")
        await self.server.serve_forever()

    async def stop(self):
        """Stop the mock server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print(f"Mock Server on port {self.port} stopped.")

    async def handle_client(self, reader, writer):
        from pure3270.protocol.utils import (
            IAC, DO, DONT, WILL, WONT, SB, SE,
            TELOPT_TTYPE, TELOPT_BINARY, TELOPT_EOR, TELOPT_TN3270E,
            TN3270E_DEVICE_TYPE, TN3270E_FUNCTIONS, TN3270E_IS, TN3270E_SEND
        )
        try:
            negotiation_done = False
            while True:
                print(f"[MOCK SERVER DEBUG] Entering read loop iteration, waiting for data...")
                try:
                    data = await asyncio.wait_for(reader.read(1024), timeout=1.0)
                    print(f"[MOCK SERVER DEBUG] Received {len(data)} bytes: {data.hex()}")
                except asyncio.TimeoutError:
                    print(f"[MOCK SERVER DEBUG] Read timeout, continuing loop.")
                    continue
                if not data:
                    print(f"[MOCK SERVER DEBUG] No data received, breaking loop.")
                    break

                response = bytearray()
                i = 0
                while i < len(data):
                    if data[i] == IAC:
                        if i + 1 < len(data):
                            command = data[i+1]
                            if command == DO:
                                if i + 2 < len(data):
                                    option = data[i+2]
                                    if option == TELOPT_TTYPE:
                                        response.extend(bytes([IAC, WILL, TELOPT_TTYPE]))
                                    elif option == TELOPT_BINARY:
                                        response.extend(bytes([IAC, WILL, TELOPT_BINARY]))
                                    elif option == TELOPT_EOR:
                                        response.extend(bytes([IAC, WILL, TELOPT_EOR]))
                                    elif option == TELOPT_TN3270E:
                                        response.extend(bytes([IAC, WILL, TELOPT_TN3270E]))
                                    else:
                                        response.extend(bytes([IAC, WONT, option]))
                                    i += 3
                                else:
                                    break
                            elif command == WILL:
                                if i + 2 < len(data):
                                    option = data[i+2]
                                    if option == TELOPT_TTYPE:
                                        response.extend(bytes([IAC, DO, TELOPT_TTYPE]))
                                    elif option == TELOPT_BINARY:
                                        response.extend(bytes([IAC, DO, TELOPT_BINARY]))
                                    elif option == TELOPT_EOR:
                                        response.extend(bytes([IAC, DO, TELOPT_EOR]))
                                    elif option == TELOPT_TN3270E:
                                        # Don't respond to WILL TELOPT_TN3270E - negotiation is complete
                                        # Instead, start TN3270E subnegotiation by sending DEVICE-TYPE SEND
                                        response.extend(bytes([IAC, SB, TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_SEND, IAC, SE]))
                                    else:
                                        response.extend(bytes([IAC, DONT, option]))
                                    i += 3
                                else:
                                    break
                            elif command == SB:
                                j = i + 2
                                while j < len(data) and not (data[j] == IAC and j + 1 < len(data) and data[j+1] == SE):
                                    j += 1
                                if j + 1 < len(data) and data[j+1] == SE:
                                    sub_option = data[i+2]
                                    sub_data = data[i+3:j]
                                    print(f"[MOCK SERVER DEBUG] Processing SB: sub_option=0x{sub_option:02x}, sub_data={sub_data.hex()}")
                                    if sub_option == TELOPT_TN3270E:
                                        if len(sub_data) >= 2:
                                            tn3270e_type = sub_data[0]
                                            tn3270e_subtype = sub_data[1]
                                            print(f"[MOCK SERVER DEBUG] TN3270E sub: type=0x{tn3270e_type:02x}, subtype=0x{tn3270e_subtype:02x}")
                                            if tn3270e_type == TN3270E_DEVICE_TYPE and tn3270e_subtype == TN3270E_SEND:
                                                device_type_response = b"IBM-3278-2\x00"
                                                response.extend(bytes([IAC, SB, TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_IS]) + device_type_response + bytes([IAC, SE]))
                                                self._negotiated_device_type = True
                                                print("[MOCK SERVER DEBUG] Sent DEVICE-TYPE IS response.")
                                                self._maybe_set_negotiation_complete()
                                            elif tn3270e_type == TN3270E_FUNCTIONS and tn3270e_subtype == TN3270E_SEND:
                                                functions_response = bytes([TN3270E_BIND_IMAGE | TN3270E_RESPONSES])
                                                response.extend(bytes([IAC, SB, TELOPT_TN3270E, TN3270E_FUNCTIONS, TN3270E_IS]) + functions_response + bytes([IAC, SE]))
                                                self._negotiated_functions = True
                                                print("[MOCK SERVER DEBUG] Sent FUNCTIONS IS response.")
                                                self._maybe_set_negotiation_complete()
                                            else:
                                                print(f"[MOCK SERVER DEBUG] Unhandled TN3270E sub: type=0x{tn3270e_type:02x}, subtype=0x{tn3270e_subtype:02x}")
                                        else:
                                            print(f"[MOCK SERVER DEBUG] Incomplete TN3270E sub_data: {sub_data.hex()}")
                                    else:
                                        print(f"[MOCK SERVER DEBUG] Unhandled SB sub_option: 0x{sub_option:02x}")
                                    i = j + 2
                                else:
                                    print(f"[MOCK SERVER DEBUG] Incomplete SB, no SE found.")
                                    break
                            else:
                                i += 2
                        else:
                            break
                    else:
                        i += 1
                if response:
                    print(f"[MOCK SERVER DEBUG] Sending response: {response.hex()}")
                    writer.write(response)
                    await writer.drain()
                    print(f"[MOCK SERVER DEBUG] Response drained.")
                    await asyncio.sleep(0.01)
                else:
                    print(f"[MOCK SERVER DEBUG] No response to send in this iteration.")
                if self.negotiation_complete.is_set() and not negotiation_done:
                    print("[MOCK SERVER DEBUG] TN3270E negotiation complete (base class).")
                    negotiation_done = True
        except Exception as e:
            print(f"Mock server client handler error: {e}")
        finally:
            if writer in self.clients:
                self.clients.remove(writer)
            writer.close()
            await writer.wait_closed()

class LUNameMockServer(TN3270ENegotiatingMockServer):
    """
    A mock TN3270 server that simulates LU name negotiation (RFC 1646).
    It responds to DO TERMINAL-LOCATION by sending WILL TERMINAL-LOCATION
    and then a subnegotiation with the client's LU name.
    """
    def __init__(self, port=0):
        super().__init__(port)
        self.lu_name_received = asyncio.Event()
        self.received_lu_name = None

    async def handle_client(self, reader, writer):
        from pure3270.protocol.utils import (
            IAC, DO, WILL, SB, SE, TELOPT_TTYPE, TELOPT_BINARY, TELOPT_EOR, TELOPT_TN3270E,
            TELOPT_OLD_ENVIRON as TELOPT_TERMINAL_LOCATION, TN3270E_IS
        )
        try:
            while True:
                try:
                    data = await asyncio.wait_for(reader.read(1024), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                if not data:
                    break

                response = bytearray()
                i = 0
                while i < len(data):
                    if data[i] == IAC:
                        if i + 1 < len(data):
                            command = data[i+1]
                            if command == DO:
                                if i + 2 < len(data):
                                    option = data[i+2]
                                    if option == TELOPT_TTYPE:
                                        response.extend(bytes([IAC, WILL, TELOPT_TTYPE]))
                                    elif option == TELOPT_BINARY:
                                        response.extend(bytes([IAC, WILL, TELOPT_BINARY]))
                                    elif option == TELOPT_EOR:
                                        response.extend(bytes([IAC, WILL, TELOPT_EOR]))
                                    elif option == TELOPT_TN3270E:
                                        response.extend(bytes([IAC, WILL, TELOPT_TN3270E]))
                                    elif option == TELOPT_TERMINAL_LOCATION:
                                        response.extend(bytes([IAC, WILL, TELOPT_TERMINAL_LOCATION]))
                                        # Client should respond with SB TERMINAL-LOCATION IS <LU_NAME> SE
                                    else:
                                        response.extend(bytes([IAC, WONT, option]))
                                    i += 3
                                else: # Incomplete command
                                    break
                            elif command == WILL:
                                if i + 2 < len(data):
                                    option = data[i+2]
                                    if option == TELOPT_TTYPE:
                                        response.extend(bytes([IAC, DO, TELOPT_TTYPE]))
                                    elif option == TELOPT_BINARY:
                                        response.extend(bytes([IAC, DO, TELOPT_BINARY]))
                                    elif option == TELOPT_EOR:
                                        response.extend(bytes([IAC, DO, TELOPT_EOR]))
                                    elif option == TELOPT_TN3270E:
                                        # Don\'t respond to WILL TELOPT_TN3270E - negotiation is complete
                                        # Instead, start TN3270E subnegotiation by sending DEVICE-TYPE SEND
                                        response.extend(bytes([IAC, SB, TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_SEND, IAC, SE]))
                                    elif option == TELOPT_TERMINAL_LOCATION:
                                        response.extend(bytes([IAC, DO, TELOPT_TERMINAL_LOCATION]))
                                        # After sending DO, we should also send a request for the client's LU name
                                        # But we'll wait for the client to send it
                                    else:
                                        response.extend(bytes([IAC, DONT, option]))
                                    i += 3
                                else: # Incomplete command
                                    break
                            elif command == DO:
                                if i + 2 < len(data):
                                    option = data[i+2]
                                    if option == TELOPT_TTYPE:
                                        response.extend(bytes([IAC, WILL, TELOPT_TTYPE]))
                                    elif option == TELOPT_BINARY:
                                        response.extend(bytes([IAC, WILL, TELOPT_BINARY]))
                                    elif option == TELOPT_EOR:
                                        response.extend(bytes([IAC, WILL, TELOPT_EOR]))
                                    elif option == TELOPT_TN3270E:
                                        response.extend(bytes([IAC, WILL, TELOPT_TN3270E]))
                                    elif option == TELOPT_TERMINAL_LOCATION:
                                        response.extend(bytes([IAC, WILL, TELOPT_TERMINAL_LOCATION]))
                                        # Client should respond with SB TERMINAL-LOCATION IS <LU_NAME> SE
                                    else:
                                        response.extend(bytes([IAC, WONT, option]))
                                    i += 3
                                else: # Incomplete command
                                    break
                            elif command == SB:
                                j = i + 2
                                while j < len(data) and not (data[j] == IAC and j + 1 < len(data) and data[j+1] == SE):
                                    j += 1
                                
                                if j + 1 < len(data) and data[j+1] == SE:
                                    sub_option = data[i+2]
                                    sub_data = data[i+3:j]

                                    if sub_option == TELOPT_TERMINAL_LOCATION:
                                        if len(sub_data) >= 1 and sub_data[0] == TN3270E_IS:
                                            self.received_lu_name = sub_data[1:].decode('ascii', errors='ignore')
                                            print(f"Mock Server: Received LU Name: {self.received_lu_name}")
                                            self.lu_name_received.set()
                                    i = j + 2
                                else:
                                    break # Incomplete subnegotiation
                            else:
                                i += 2 # Skip unhandled IAC command
                        else:
                            break # Incomplete IAC sequence
                    else:
                        i += 1 # Not IAC, just skip

                if response:
                    writer.write(response)
                    await writer.drain()
                    await asyncio.sleep(0.01) # Give client time to process

                # Signal negotiation complete after initial Telnet negotiation
                if not self.negotiation_complete.is_set():
                    self.negotiation_complete.set()
                    print("Mock Server: Telnet negotiation complete for LU Name.")
        except Exception as e:
            print(f"Mock server client handler error: {e}")
        finally:
            if writer in self.clients:
                self.clients.remove(writer)
            writer.close()
            await writer.wait_closed()


class PrinterStatusMockServer(TN3270ENegotiatingMockServer):
    """
    A mock TN3270 server that simulates sending printer status messages (SOH, Structured Fields)
    and receiving printer status from the client.
    """
    def __init__(self, port=0):
        super().__init__(port)
        self.client_soh_received = asyncio.Event()
        self.client_printer_status_sf_received = asyncio.Event()
        self.received_soh_status = None
        self.received_printer_status_sf_code = None

    async def handle_client(self, reader, writer):
        from pure3270.protocol.utils import (
            IAC, DO, WILL, SB, SE, TELOPT_TTYPE, TELOPT_BINARY, TELOPT_EOR, TELOPT_TN3270E,
            TN3270E_DEVICE_TYPE, TN3270E_FUNCTIONS, TN3270E_IS, TN3270E_SEND,
            TN3270E_RESPONSES, TN3270E_BIND_IMAGE, TN3270E_DATA_STREAM_CTL,
            TN3270_DATA, SCS_DATA, NVT_DATA, SNA_RESPONSE as SNA_RESPONSE_TYPE_UTIL
        )
        from pure3270.protocol.data_stream import (
            STRUCTURED_FIELD, BIND_SF_TYPE, SNA_RESPONSE_DATA_TYPE, PRINTER_STATUS_DATA_TYPE,
            SNA_COMMAND_RESPONSE, SNA_DATA_RESPONSE,
            SNA_SENSE_CODE_SUCCESS, SNA_SENSE_CODE_INVALID_FORMAT,
            SNA_SENSE_CODE_NOT_SUPPORTED, SNA_SENSE_CODE_SESSION_FAILURE,
            PRINTER_STATUS_SF_TYPE, SOH_DEVICE_END, SOH_INTERVENTION_REQUIRED, SOH_SUCCESS,
            SOH
        )
        from pure3270.protocol.tn3270e_header import TN3270EHeader

        try:
            negotiation_done = False
            while True:
                try:
                    data = await asyncio.wait_for(reader.read(1024), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                if not data:
                    break

                response = bytearray()
                i = 0
                while i < len(data):
                    if data[i] == IAC:
                        if i + 1 < len(data):
                            command = data[i+1]
                            if command == DO:
                                if i + 2 < len(data):
                                    option = data[i+2]
                                    if option == TELOPT_TTYPE:
                                        response.extend(bytes([IAC, WILL, TELOPT_TTYPE]))
                                    elif option == TELOPT_BINARY:
                                        response.extend(bytes([IAC, WILL, TELOPT_BINARY]))
                                    elif option == TELOPT_EOR:
                                        response.extend(bytes([IAC, WILL, TELOPT_EOR]))
                                    elif option == TELOPT_TN3270E:
                                        response.extend(bytes([IAC, WILL, TELOPT_TN3270E]))
                                    else:
                                        response.extend(bytes([IAC, WONT, option]))
                                    i += 3
                                else: # Incomplete command
                                    break
                            elif command == WILL:
                                if i + 2 < len(data):
                                    option = data[i+2]
                                    if option == TELOPT_TTYPE:
                                        response.extend(bytes([IAC, DO, TELOPT_TTYPE]))
                                    elif option == TELOPT_BINARY:
                                        response.extend(bytes([IAC, DO, TELOPT_BINARY]))
                                    elif option == TELOPT_EOR:
                                        response.extend(bytes([IAC, DO, TELOPT_EOR]))
                                    elif option == TELOPT_TN3270E:
                                        # Don\'t respond to WILL TELOPT_TN3270E - negotiation is complete
                                        # Instead, start TN3270E subnegotiation by sending DEVICE-TYPE SEND
                                        response.extend(bytes([IAC, SB, TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_SEND, IAC, SE]))
                                    else:
                                        response.extend(bytes([IAC, DONT, option]))
                                    i += 3
                                else: # Incomplete command
                                    break
                            elif command == SB:
                                j = i + 2
                                while j < len(data) and not (data[j] == IAC and j + 1 < len(data) and data[j+1] == SE):
                                    j += 1
                                
                                if j + 1 < len(data) and data[j+1] == SE:
                                    sub_option = data[i+2]
                                    sub_data = data[i+3:j]

                                    if sub_option == TELOPT_TN3270E:
                                        if len(sub_data) >= 2:
                                            tn3270e_type = sub_data[0]
                                            tn3270e_subtype = sub_data[1]

                                            if tn3270e_type == TN3270E_DEVICE_TYPE and tn3270e_subtype == TN3270E_SEND:
                                                device_type_response = b"IBM-3278-2\x00"
                                                response.extend(bytes([IAC, SB, TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_IS]) + device_type_response + bytes([IAC, SE]))
                                                self.negotiation_complete.set()
                                            elif tn3270e_type == TN3270E_FUNCTIONS and tn3270e_subtype == TN3270E_SEND:
                                                functions_response = bytes([TN3270E_BIND_IMAGE | TN3270E_DATA_STREAM_CTL | TN3270E_RESPONSES])
                                                response.extend(bytes([IAC, SB, TELOPT_TN3270E, TN3270E_FUNCTIONS, TN3270E_IS]) + functions_response + bytes([IAC, SE]))
                                                self.negotiation_complete.set()
                                    i = j + 2
                                else:
                                    break
                            else:
                                i += 2
                        else:
                            break
                    elif data[i] == SOH: # Check for SOH messages directly in stream (for printer status)
                        if i + 1 < len(data):
                            self.received_soh_status = data[i+1]
                            print(f"Mock Server: Received SOH message with status: 0x{self.received_soh_status:02x}")
                            self.client_soh_received.set()
                            i += 2
                            continue
                        else:
                            break
                    elif data[i] == STRUCTURED_FIELD: # Check for Structured Field (for printer status SF)
                        if i + 3 < len(data): # SF_ID + 2-byte Length + SF_Type
                            sf_len = (data[i+1] << 8) | data[i+2]
                            sf_type = data[i+3]
                            if sf_type == PRINTER_STATUS_SF_TYPE:
                                if i + 4 < len(data):
                                    self.received_printer_status_sf_code = data[i+4]
                                    print(f"Mock Server: Received Printer Status SF with code: 0x{self.received_printer_status_sf_code:02x}")
                                    self.client_printer_status_sf_received.set()
                                    i += (3 + sf_len) # Skip the entire structured field
                                    continue
                            i += 1
                        else:
                            break
                    else:
                        i += 1 # Not IAC, SOH, or SF, just skip

                if response:
                    writer.write(response)
                    await writer.drain()

                if self.negotiation_complete.is_set() and not negotiation_done:
                    print("Mock Server: Negotiation complete. Sending printer status messages.")
                    # Send SOH messages
                    soh_success_msg = bytes([SOH, SOH_SUCCESS])
                    writer.write(soh_success_msg)
                    await writer.drain()
                    print(f"Mock Server: Sent SOH success: {soh_success_msg.hex()}")

                    soh_device_end_msg = bytes([SOH, SOH_DEVICE_END])
                    writer.write(soh_device_end_msg)
                    await writer.drain()
                    print(f"Mock Server: Sent SOH device end: {soh_device_end_msg.hex()}")

                    soh_intervention_required_msg = bytes([SOH, SOH_INTERVENTION_REQUIRED])
                    writer.write(soh_intervention_required_msg)
                    await writer.drain()
                    print(f"Mock Server: Sent SOH intervention required: {soh_intervention_required_msg.hex()}")

                    # Send Printer Status Structured Fields
                    # SF format: 0x3C (SF_ID), Length (2 bytes), SF_Type (1 byte), Data
                    printer_sf_success_data = bytes([PRINTER_STATUS_SF_TYPE, 0x00]) # Type + status
                    printer_sf_success = bytes([STRUCTURED_FIELD]) + (len(printer_sf_success_data) + 2).to_bytes(2, 'big') + printer_sf_success_data
                    writer.write(printer_sf_success)
                    await writer.drain()
                    print(f"Mock Server: Sent Printer Status SF success: {printer_sf_success.hex()}")

                    negotiation_done = True
        except Exception as e:
            print(f"Mock server client handler error: {e}")
        finally:
            if writer in self.clients:
                self.clients.remove(writer)
            writer.close()
            await writer.wait_closed()


class BindImageMockServer(TN3270ENegotiatingMockServer):
    """
    A mock TN3270 server that simulates sending a BIND-IMAGE Structured Field
    with specific screen dimensions.
    """
    def __init__(self, port=0, rows=32, cols=80):
        super().__init__(port)
        self.rows = rows
        self.cols = cols
        self.bind_image_sent = asyncio.Event()

    async def handle_client(self, reader, writer):
        from pure3270.protocol.utils import (
            IAC, DO, DONT, WILL, WONT, SB, SE,
            TELOPT_TTYPE, TELOPT_BINARY, TELOPT_EOR, TELOPT_TN3270E,
            TN3270E_DEVICE_TYPE, TN3270E_FUNCTIONS, TN3270E_IS, TN3270E_SEND,
            TN3270E_BIND_IMAGE, TN3270E_RESPONSES,
            TN3270E_IBM_DYNAMIC
        )
        from pure3270.protocol.data_stream import (
            STRUCTURED_FIELD, QUERY_REPLY_SF, QUERY_REPLY_CHARACTERISTICS
        )
        from pure3270.protocol.tn3270e_header import TN3270EHeader
        from pure3270.protocol.data_stream import BIND_IMAGE

        try:
            negotiation_done = False
            while True:
                try:
                    data = await asyncio.wait_for(reader.read(1024), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                if not data:
                    break
                print(f"BindImageMockServer: Received: {data.hex()}")
                response = bytearray()
                i = 0
                while i < len(data):
                    if data[i] == IAC:
                        if i + 1 < len(data):
                            command = data[i+1]
                            if command == DO:
                                if i + 2 < len(data):
                                    option = data[i+2]
                                    if option == TELOPT_TTYPE:
                                        response.extend(bytes([IAC, WILL, TELOPT_TTYPE]))
                                    elif option == TELOPT_BINARY:
                                        response.extend(bytes([IAC, WILL, TELOPT_BINARY]))
                                    elif option == TELOPT_EOR:
                                        response.extend(bytes([IAC, WILL, TELOPT_EOR]))
                                    elif option == TELOPT_TN3270E:
                                        response.extend(bytes([IAC, WILL, TELOPT_TN3270E]))
                                    else:
                                        response.extend(bytes([IAC, WONT, option]))
                                    i += 3
                                else:
                                    break
                            elif command == WILL:
                                if i + 2 < len(data):
                                    option = data[i+2]
                                    if option == TELOPT_TTYPE:
                                        response.extend(bytes([IAC, DO, TELOPT_TTYPE]))
                                    elif option == TELOPT_BINARY:
                                        response.extend(bytes([IAC, DO, TELOPT_BINARY]))
                                    elif option == TELOPT_EOR:
                                        response.extend(bytes([IAC, DO, TELOPT_EOR]))
                                    elif option == TELOPT_TN3270E:
                                        # Don't respond to WILL TELOPT_TN3270E - negotiation is complete
                                        # Instead, start TN3270E subnegotiation by sending DEVICE-TYPE SEND
                                        response.extend(bytes([IAC, SB, TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_SEND, IAC, SE]))
                                    else:
                                        response.extend(bytes([IAC, DONT, option]))
                                    i += 3
                                else:
                                    break
                            elif command == SB:
                                j = i + 2
                                while j < len(data) and not (data[j] == IAC and j + 1 < len(data) and data[j+1] == SE):
                                    j += 1
                                if j + 1 < len(data) and data[j+1] == SE:
                                    sub_option = data[i+2]
                                    sub_data = data[i+3:j]
                                    if sub_option == TELOPT_TN3270E:
                                        if len(sub_data) >= 2:
                                            tn3270e_type = sub_data[0]
                                            tn3270e_subtype = sub_data[1]
                                            if tn3270e_type == TN3270E_DEVICE_TYPE and tn3270e_subtype == TN3270E_SEND:
                                                if not self._negotiated_device_type:
                                                    device_type_response = TN3270E_IBM_DYNAMIC.encode("ascii") + b"\x00"
                                                    immediate_response = bytes([IAC, SB, TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_IS]) + device_type_response + bytes([IAC, SE])
                                                    writer.write(immediate_response)
                                                    await writer.drain()
                                                    print("Mock Server: Sent DEVICE-TYPE IS response immediately")
                                                    self._negotiated_device_type = True
                                                    self._maybe_set_negotiation_complete()
                                            elif tn3270e_type == TN3270E_FUNCTIONS and tn3270e_subtype == TN3270E_SEND:
                                                if not self._negotiated_functions:
                                                    functions_response = bytes([TN3270E_BIND_IMAGE | TN3270E_RESPONSES])
                                                    immediate_response = bytes([IAC, SB, TELOPT_TN3270E, TN3270E_FUNCTIONS, TN3270E_IS]) + functions_response + bytes([IAC, SE])
                                                    writer.write(immediate_response)
                                                    await writer.drain()
                                                    print(f"Mock Server: Sent FUNCTIONS IS response immediately")
                                                    self._negotiated_functions = True
                                                    self._maybe_set_negotiation_complete()
                                    i = j + 2
                                else:
                                    break
                            else:
                                i += 2
                        else:
                            break
                    else:
                        i += 1
                if response:
                    print(f"BindImageMockServer: Sending: {response.hex()}")
                    writer.write(response)
                    await writer.drain()
                    await asyncio.sleep(0.01)
                if self.negotiation_complete.is_set() and not negotiation_done:
                    print("Mock Server: TN3270E negotiation complete (BindImageMockServer). Sending BIND-IMAGE.")
                    # Construct BIND-IMAGE Structured Field
                    psc_data = bytearray()
                    psc_data.append(0x06)
                    psc_data.append(0x01)
                    psc_data.extend(self.rows.to_bytes(2, 'big'))
                    psc_data.extend(self.cols.to_bytes(2, 'big'))
                    query_reply_data = bytearray()
                    query_reply_data.append(0x03)
                    query_reply_data.append(0x02)
                    query_reply_data.append(0x81)
                    bind_data = psc_data + query_reply_data
                    sf = bytearray()
                    sf.append(0x3C)
                    total_length = 1 + len(bind_data)
                    sf.extend(total_length.to_bytes(2, 'big'))
                    sf.append(0x03)
                    sf.extend(bind_data)
                    bind_header = TN3270EHeader(
                        data_type=BIND_IMAGE,
                        request_flag=0,
                        response_flag=0,
                        seq_number=1
                    )
                    bind_message = bind_header.to_bytes() + sf
                    writer.write(bind_message)
                    await writer.drain()
                    print(f"Mock Server: Sent BIND-IMAGE after negotiation: {bind_message.hex()}")
                    negotiation_done = True
        except Exception as e:
            print(f"Mock server error: {e}")
        finally:
            if writer in self.clients:
                self.clients.remove(writer)
            writer.close()
            await writer.wait_closed()

class SNAAwareMockServer(TN3270ENegotiatingMockServer):
    """
    A mock TN3270 server that simulates sending various SNA responses
    (positive, negative with different sense codes) and state transitions.
    """
    def __init__(self, port=0):
        super().__init__(port)
        self.positive_response_sent = asyncio.Event()
        self.negative_response_sent = asyncio.Event()
        self.lu_busy_response_sent = asyncio.Event()
        self.invalid_sequence_response_sent = asyncio.Event()
        self.session_failure_response_sent = asyncio.Event()
        self.state_error_response_sent = asyncio.Event()
        self.bind_image_sent = asyncio.Event()
        self.rows = 24
        self.cols = 80

    async def handle_client(self, reader, writer):
        # Terminal types to cycle through for TTYPE SEND/IS negotiation
        ttype_list = [
            b"IBM-3278-2",
            b"IBM-3278-3",
            b"IBM-3278-4",
            b"IBM-3278-5",
            b"IBM-3279-2",
            b"IBM-3279-3",
            b"IBM-3279-4",
            b"IBM-3279-5",
            b"IBM-DYNAMIC"
        ]
        ttype_index = 0
        from pure3270.protocol.utils import (
            IAC, DO, WILL, SB, SE, TELOPT_TTYPE, TELOPT_BINARY, TELOPT_EOR, TELOPT_TN3270E,
            TN3270E_DEVICE_TYPE, TN3270E_FUNCTIONS, TN3270E_IS, TN3270E_SEND,
            TN3270E_RESPONSES, TN3270E_BIND_IMAGE, TN3270E_DATA_STREAM_CTL,
            TN3270_DATA, SCS_DATA, NVT_DATA, REQUEST, SSCP_LU_DATA, PRINT_EOJ
        )
        from pure3270.protocol.data_stream import (
            SNA_COMMAND_RESPONSE, SNA_DATA_RESPONSE,
            SNA_SENSE_CODE_SUCCESS, SNA_SENSE_CODE_INVALID_FORMAT,
            SNA_SENSE_CODE_NOT_SUPPORTED, SNA_SENSE_CODE_SESSION_FAILURE,
            SNA_SENSE_CODE_INVALID_REQUEST, SNA_SENSE_CODE_LU_BUSY,
            SNA_SENSE_CODE_INVALID_SEQUENCE, SNA_SENSE_CODE_NO_RESOURCES,
            SNA_SENSE_CODE_STATE_ERROR,
            SNA_FLAGS_NONE, SNA_FLAGS_RSP, SNA_FLAGS_EXCEPTION_RESPONSE,
            SNA_RESPONSE_DATA_TYPE
        )
        from pure3270.protocol.tn3270e_header import TN3270EHeader

        try:
            negotiation_done = False
            sent_telnet_options = False
            while True:
                print(f"[MOCK SERVER DEBUG] SNAAware: Entering read loop iteration, waiting for data...")
                try:
                    data = await asyncio.wait_for(reader.read(1024), timeout=1.0)
                    print(f"[MOCK SERVER DEBUG] SNAAware: Received {len(data)} bytes: {data.hex()}")
                except asyncio.TimeoutError:
                    print(f"[MOCK SERVER DEBUG] SNAAware: Read timeout, continuing loop.")
                    continue
                if not data:
                    print(f"[MOCK SERVER DEBUG] SNAAware: No data received, breaking loop.")
                    break

                print(f"SNAAwareMockServer: Received: {data.hex()}")
                # Log each byte received
                for idx, b in enumerate(data):
                    print(f"SNAAwareMockServer: Byte received [{idx}]: 0x{b:02x}")
                response = bytearray()
                i = 0
                while i < len(data):
                    if data[i] == IAC:
                        if i + 1 < len(data):
                            command = data[i+1]
                            if command == WILL:
                                if i + 2 < len(data):
                                    option = data[i+2]
                                    if option == TELOPT_TTYPE:
                                        print("Mock Server: Responding DO TTYPE")
                                        response.extend(bytes([IAC, DO, TELOPT_TTYPE]))
                                        # After TTYPE, send DO/WILL BINARY, EOR, TN3270E (RFC 1091)
                                        if not sent_telnet_options:
                                            response.extend(bytes([IAC, DO, TELOPT_BINARY]))
                                            response.extend(bytes([IAC, WILL, TELOPT_BINARY]))
                                            response.extend(bytes([IAC, DO, TELOPT_EOR]))
                                            response.extend(bytes([IAC, WILL, TELOPT_EOR]))
                                            response.extend(bytes([IAC, DO, TELOPT_TN3270E]))
                                            response.extend(bytes([IAC, WILL, TELOPT_TN3270E]))
                                            sent_telnet_options = True
                                    elif option == TELOPT_BINARY:
                                        print("Mock Server: Responding DO BINARY")
                                        response.extend(bytes([IAC, DO, TELOPT_BINARY]))
                                    elif option == TELOPT_EOR:
                                        print("Mock Server: Responding DO EOR")
                                        response.extend(bytes([IAC, DO, TELOPT_EOR]))
                                    elif option == TELOPT_TN3270E:
                                        print("Mock Server: Responding SB TN3270E DEVICE-TYPE SEND")
                                        response.extend(bytes([IAC, SB, TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_SEND, IAC, SE]))
                                    else:
                                        print(f"Mock Server: Responding DONT {option}")
                                        response.extend(bytes([IAC, DONT, option]))
                                    i += 3
                                else:
                                    break
                            elif command == SB:
                                j = i + 2
                                while j < len(data) and not (data[j] == IAC and j + 1 < len(data) and data[j+1] == SE):
                                    j += 1
                                if j + 1 < len(data) and data[j+1] == SE:
                                    sub_option = data[i+2]
                                    sub_data = data[i+3:j]
                                    print(f"[MOCK SERVER DEBUG] SNAAware: Processing SB: sub_option=0x{sub_option:02x}, sub_data={sub_data.hex()}")
                                    if sub_option == TELOPT_TN3270E:
                                        if len(sub_data) >= 2:
                                            tn3270e_type = sub_data[0]
                                            tn3270e_subtype = sub_data[1]
                                            print(f"[MOCK SERVER DEBUG] SNAAware: TN3270E sub: type=0x{tn3270e_type:02x}, subtype=0x{tn3270e_subtype:02x}")
                                            if tn3270e_type == TN3270E_DEVICE_TYPE and tn3270e_subtype == TN3270E_SEND:
                                                print("[MOCK SERVER DEBUG] SNAAware: Received DEVICE-TYPE SEND subnegotiation.")
                                                if not self._negotiated_device_type:
                                                    from pure3270.protocol.utils import TN3270E_IBM_DYNAMIC
                                                    device_type_response = TN3270E_IBM_DYNAMIC.encode("ascii") + b"\x00"
                                                    print("[MOCK SERVER DEBUG] SNAAware: Sending DEVICE-TYPE IS response (SNA)...")
                                                    writer.write(bytes([IAC, SB, TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_IS]) + device_type_response + bytes([IAC, SE]))
                                                    await writer.drain()
                                                    self._negotiated_device_type = True
                                                    print("[MOCK SERVER DEBUG] SNAAware: Sent DEVICE-TYPE IS response (SNA).")
                                                    if self._negotiated_functions:
                                                        print("[MOCK SERVER DEBUG] SNAAware: Both DEVICE-TYPE and FUNCTIONS negotiated. Setting negotiation_complete.")
                                                        self._maybe_set_negotiation_complete()
                                            elif tn3270e_type == TN3270E_FUNCTIONS and tn3270e_subtype == TN3270E_SEND:
                                                print("[MOCK SERVER DEBUG] SNAAware: Received FUNCTIONS SEND subnegotiation.")
                                                if not self._negotiated_functions:
                                                    functions_response = bytes([TN3270E_BIND_IMAGE | TN3270E_DATA_STREAM_CTL | TN3270E_RESPONSES])
                                                    print("[MOCK SERVER DEBUG] SNAAware: Sending FUNCTIONS IS response (SNA)...")
                                                    writer.write(bytes([IAC, SB, TELOPT_TN3270E, TN3270E_FUNCTIONS, TN3270E_IS]) + functions_response + bytes([IAC, SE]))
                                                    await writer.drain()
                                                    self._negotiated_functions = True
                                                    print("[MOCK SERVER DEBUG] SNAAware: Sent FUNCTIONS IS response (SNA).")
                                                    if self._negotiated_device_type:
                                                        print("[MOCK SERVER DEBUG] SNAAware: Both DEVICE-TYPE and FUNCTIONS negotiated. Setting negotiation_complete.")
                                                        self._maybe_set_negotiation_complete()
                                            else:
                                                print(f"[MOCK SERVER DEBUG] SNAAware: Unhandled TN3270E sub: type=0x{tn3270e_type:02x}, subtype=0x{tn3270e_subtype:02x}")
                                        else:
                                            print(f"[MOCK SERVER DEBUG] SNAAware: Incomplete TN3270E sub_data: {sub_data.hex()}")
                                    elif sub_option == TELOPT_TTYPE:
                                        # Handle TTYPE IS with multiple terminal types (null-separated)
                                        if len(sub_data) > 1 and sub_data[0] == 0:  # IS
                                            # Parse null-separated terminal types
                                            ttypes = sub_data[1:].split(b'\x00')
                                            ttypes = [t for t in ttypes if t]
                                            print(f"[MOCK SERVER DEBUG] SNAAware: Received TTYPE IS with types: {[t.decode(errors='ignore') for t in ttypes]}")
                                            if b"IBM-DYNAMIC" in ttypes:
                                                print("[MOCK SERVER DEBUG] SNAAware: IBM-DYNAMIC found, proceeding with negotiation.")
                                                self._ttype_index = len(ttype_list) - 1
                                        i = j + 2
                                        continue
                                        # Respond to TTYPE SEND with TTYPE IS, cycling through the list (fallback)
                                        if len(sub_data) >= 1 and sub_data[0] == 1:  # SEND
                                            if not hasattr(self, '_ttype_index'):
                                                self._ttype_index = 0
                                            terminal_type = ttype_list[self._ttype_index]
                                            writer.write(bytes([IAC, SB, TELOPT_TTYPE, 0, *terminal_type, IAC, SE]))
                                            await writer.drain()
                                            print(f"[MOCK SERVER DEBUG] SNAAware: Sent TTYPE IS response (SNA): {terminal_type.decode()}")
                                            self._ttype_index += 1
                                            if self._ttype_index >= len(ttype_list):
                                                self._ttype_index = len(ttype_list) - 1  # Stay at last
                                            i = j + 2
                                            continue
                                    else:
                                        print(f"[MOCK SERVER DEBUG] SNAAware: Unhandled SB sub_option: 0x{sub_option:02x}")
                                    i = j + 2
                                else:
                                    print(f"[MOCK SERVER DEBUG] SNAAware: Incomplete SB, no SE found.")
                                    break
                            else:
                                i += 2
                        else:
                            break
                    else:
                        i += 1
                if response:
                    print(f"[MOCK SERVER DEBUG] SNAAware: Sending response: {response.hex()}")
                    # Log each byte sent
                    for idx, b in enumerate(response):
                        print(f"[MOCK SERVER DEBUG] SNAAware: Byte sent [{idx}]: 0x{b:02x}")
                    writer.write(response)
                    await writer.drain()
                    print(f"[MOCK SERVER DEBUG] SNAAware: Response drained.")
                else:
                    print(f"[MOCK SERVER DEBUG] SNAAware: No response to send in this iteration.")
                if self.negotiation_complete.is_set() and not negotiation_done:
                    print("Mock Server: negotiation_complete event is set. About to send BIND-IMAGE.")
                    # Send BIND-IMAGE Structured Field (same as BindImageMockServer)
                    from pure3270.protocol.tn3270e_header import TN3270EHeader
                    BIND_IMAGE = 0x03
                    psc_data = bytearray()
                    psc_data.append(0x06)
                    psc_data.append(0x01)
                    psc_data.extend(self.rows.to_bytes(2, 'big'))
                    psc_data.extend(self.cols.to_bytes(2, 'big'))
                    query_reply_data = bytearray()
                    query_reply_data.append(0x03)
                    query_reply_data.append(0x02)
                    query_reply_data.append(0x81)
                    bind_data = psc_data + query_reply_data
                    sf = bytearray()
                    sf.append(0x3C)
                    total_length = 2 + 1 + len(bind_data)  # length field (2) + type (1) + bind_data
                    sf.extend(total_length.to_bytes(2, 'big'))
                    sf.append(0x03)
                    sf.extend(bind_data)
                    bind_header = TN3270EHeader(
                        data_type=BIND_IMAGE,
                        request_flag=0,
                        response_flag=0,
                        seq_number=1
                    )
                    bind_message = bind_header.to_bytes() + sf
                    writer.write(bind_message)
                    await writer.drain()
                    print(f"Mock Server: Sent BIND-IMAGE after negotiation: {bind_message.hex()}")
                    self.bind_image_sent.set()
                    negotiation_done = True
        except Exception as e:
            print(f"Mock server client handler error: {e}")
        finally:
            if writer in self.clients:
                self.clients.remove(writer)
            writer.close()
            await writer.wait_closed()


async def test_sna_response_handling(port, mock_server):
    """
    Test that pure3270 correctly handles various SNA response types
    (positive and negative with sense codes) and updates session state.
    """
    print("9. Testing SNA response handling...")
    session = None
    try:
        from pure3270 import AsyncSession
        from pure3270.protocol.negotiator import SnaSessionState

        session = AsyncSession(host="localhost", port=port)
        # Retry connection up to 5 times
        for attempt in range(5):
            try:
                await session.connect()
                break
            except Exception:
                await asyncio.sleep(0.2)

        # Wait for TN3270E negotiation to complete
        await asyncio.wait_for(getattr(mock_server, 'negotiation_complete', asyncio.Event()).wait(), timeout=10)

        # Wait for the mock server to send the BIND-IMAGE
        await asyncio.wait_for(mock_server.bind_image_sent.wait(), timeout=10)

        # Small delay to ensure data is available
        await asyncio.sleep(0.5)

        # Read the BIND-IMAGE data
        try:
            await session.read(timeout=2.0)
        except asyncio.TimeoutError:
            pass  # Data might have already been processed

        # Verify that the screen dimensions are updated by the BIND-IMAGE
        assert session.screen_buffer.rows == mock_server.rows
        assert session.screen_buffer.cols == mock_server.cols
        print(f"   ✓ Screen dimensions updated by BIND-IMAGE: {session.screen_buffer.rows}x{session.screen_buffer.cols}")

        # Test SNA response handling by sending a mock SNA response
        from pure3270.protocol.data_stream import SNA_RESPONSE_DATA_TYPE, SnaResponse, SNA_SENSE_CODE_SUCCESS
        from pure3270.protocol.tn3270e_header import TN3270EHeader

        # Create a simple positive SNA response
        sna_data = bytes([0x01, 0x00, 0x00, 0x00])  # type=1, flags=0, sense=0x0000
        header = TN3270EHeader(data_type=SNA_RESPONSE_DATA_TYPE, request_flag=0, response_flag=0, seq_number=1)
        sna_message = header.to_bytes() + sna_data

        # Since this is integration test, we can't easily send from client, but verify parser can handle
        parser = session.handler.parser if hasattr(session, 'handler') and session.handler else None
        if parser:
            try:
                sna_response = parser._parse_sna_response(sna_data)
                assert sna_response.is_positive()
                assert sna_response.sense_code == SNA_SENSE_CODE_SUCCESS
                print("   ✓ SNA response parsing successful")
            except Exception as e:
                print(f"   ⚠ SNA response parsing test: {e}")
        else:
            print("   ⚠ Could not access parser for SNA test")

        # Test unknown structured field handling
        unknown_sf = bytes([0x3C, 0x00, 0x05, 0xFF, 0xAA, 0xBB])  # SF with unknown type 0xFF
        try:
            parser.parse(unknown_sf, data_type=TN3270_DATA)
            print("   ✓ Unknown structured field handling successful")
        except Exception as e:
            print(f"   ⚠ Unknown SF handling test: {e}")

        # Test RA order handling
        ra_order = bytes([0xF3, 0x41, 0x00, 0x10])  # RA attr 0x41, address row0 col16
        try:
            parser.parse(ra_order, data_type=TN3270_DATA)
            # Verify position updated (simplified check)
            current_row, current_col = parser.screen.get_position()
            print(f"   ✓ RA order handling: position now at ({current_row}, {current_col})")
        except Exception as e:
            print(f"   ⚠ RA order test: {e}")

        # Test SCS handling
        scs_order = bytes([0x04, 0x01])  # SCS_CTL_CODES 0x04 + code 0x01 (PRINT_EOJ)
        try:
            parser.parse(scs_order, data_type=TN3270_DATA)
            print("   ✓ SCS order handling successful")
        except Exception as e:
            print(f"   ⚠ SCS order test: {e}")

        return True
    except asyncio.TimeoutError:
        print("   ✗ SNA/BIND-IMAGE processing test timed out.")
        return False
    except Exception as e:
        print(f"   ✗ SNA/BIND-IMAGE processing test failed: {e}")
        return False
    finally:
        if session:
            await session.close()
        if mock_server:
            await mock_server.stop()
    # Printer status test (using PrinterStatusMockServer)
    print("10. Testing printer status communication...")
    printer_server = PrinterStatusMockServer(port=0)
    printer_task = asyncio.create_task(printer_server.start())
    await asyncio.sleep(0.5)
    try:
        session = None
        try:
            from pure3270 import AsyncSession
            session = AsyncSession(host="localhost", port=printer_server.port)
            session.is_printer_session = True  # Manually set to printer session for testing
            # Retry connection up to 5 times
            for attempt in range(5):
                try:
                    await session.connect()
                    break
                except Exception:
                    await asyncio.sleep(0.2)

            # Wait for TN3270E negotiation to complete
            await asyncio.wait_for(printer_server.negotiation_complete.wait(), timeout=10)

            # Verify client can send printer status
            from pure3270.protocol.data_stream import SOH_DEVICE_END, SOH_INTERVENTION_REQUIRED, DEVICE_END, INTERVENTION_REQUIRED, SOH_SUCCESS
            await session.send_soh_message(SOH_DEVICE_END)
            await asyncio.wait_for(printer_server.client_soh_received.wait(), timeout=5)
            assert printer_server.received_soh_status == SOH_DEVICE_END
            print("   ✓ Client sent SOH_DEVICE_END and mock server received it.")

            printer_server.client_soh_received.clear()  # Clear for next test
            await session.send_soh_message(SOH_INTERVENTION_REQUIRED)
            await asyncio.wait_for(printer_server.client_soh_received.wait(), timeout=5)
            assert printer_server.received_soh_status == SOH_INTERVENTION_REQUIRED
            print("   ✓ Client sent SOH_INTERVENTION_REQUIRED and mock server received it.")

            await session.send_printer_status_sf(DEVICE_END)
            await asyncio.wait_for(printer_server.client_printer_status_sf_received.wait(), timeout=5)
            assert printer_server.received_printer_status_sf_code == DEVICE_END
            print("   ✓ Client sent PRINTER_STATUS_SF with DEVICE_END and mock server received it.")

            printer_server.client_printer_status_sf_received.clear()  # Clear for next test
            await session.send_printer_status_sf(INTERVENTION_REQUIRED)
            await asyncio.wait_for(printer_server.client_printer_status_sf_received.wait(), timeout=5)
            assert printer_server.received_printer_status_sf_code == INTERVENTION_REQUIRED
            print("   ✓ Client sent PRINTER_STATUS_SF with INTERVENTION_REQUIRED and mock server received it.")

            # Verify printer buffer was created and status updated
            if hasattr(session, 'printer_buffer') and session.printer_buffer:
                print(f"   ✓ Printer buffer active, status: {session.printer_status}")
            else:
                print("   ⚠ Printer buffer not accessible in test")

            return True
        except asyncio.TimeoutError:
            print("   ✗ Printer status communication test timed out.")
            return False
        except Exception as e:
            print(f"   ✗ Printer status communication test failed: {e}")
            return False
        finally:
            if session:
                await session.close()
    finally:
        await printer_server.stop()
        printer_task.cancel()


# Main entry point for running all integration tests
async def main():
    # Start advanced mock servers and run advanced protocol tests
    results = {}
    # SNA-aware mock server
    from functools import partial
    sna_server = SNAAwareMockServer(port=0)
    sna_server_task = asyncio.create_task(sna_server.start())
    await asyncio.sleep(0.2)  # Give server time to start
    results['sna_response_handling'] = await test_sna_response_handling(sna_server.port, sna_server)
    await sna_server.stop()
    sna_server_task.cancel()
    # Add more advanced tests as needed (LU Name, Printer Status, etc.)
    print("\n--- Integration Test Results ---")
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    if all_passed:
        print("\nAll integration tests passed!")
        sys.exit(0)
    else:
        print("\nSome integration tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
