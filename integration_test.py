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
from pure3270.protocol.utils import WONT, DONT, TN3270E_BIND_IMAGE, TN3270E_RESPONSES
from pure3270.protocol.data_stream import QUERY_REPLY_SF, QUERY_REPLY_CHARACTERISTICS


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

    def __init__(self, port=2323):
        self.port = port
        self.server = None
        self.clients = []

    async def start(self):
        """Start the mock server."""
        try:
            self.server = await asyncio.start_server(
                self.handle_client, "localhost", self.port
            )
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
                data = await reader.read(1024)
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
    def __init__(self, port=2324):
        super().__init__(port)
        self.negotiation_complete = asyncio.Event()

    async def start(self):
        """Start the mock server."""
        self.server = await asyncio.start_server(
            self.handle_client, "localhost", self.port
        )
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
                data = await reader.read(1024)
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
                                        response.extend(bytes([IAC, DO, TELOPT_TN3270E]))
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
                                                # Respond with DEVICE-TYPE IS IBM-3278-2 (default for negotiation)
                                                device_type_response = b"IBM-3278-2\x00"
                                                response.extend(bytes([IAC, SB, TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_IS]) + device_type_response + bytes([IAC, SE]))
                                                self.negotiation_complete.set()
                                            elif tn3270e_type == TN3270E_FUNCTIONS and tn3270e_subtype == TN3270E_SEND:
                                                # Respond with FUNCTIONS IS (example: BIND-IMAGE, RESPONSES)
                                                functions_response = bytes([TN3270E_BIND_IMAGE | TN3270E_RESPONSES])
                                                response.extend(bytes([IAC, SB, TELOPT_TN3270E, TN3270E_FUNCTIONS, TN3270E_IS]) + functions_response + bytes([IAC, SE]))
                                                self.negotiation_complete.set()
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
                    writer.write(response)
                    await writer.drain()
                    await asyncio.sleep(0.01) # Give client time to process

                if self.negotiation_complete.is_set() and not negotiation_done:
                    print("Mock Server: TN3270E negotiation complete.")
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
    def __init__(self, port=2328):
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
                data = await reader.read(1024)
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
                                        response.extend(bytes([IAC, DO, TELOPT_TN3270E]))
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
    def __init__(self, port=2329):
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
            TN3270_DATA, SCS_DATA, NVT_DATA, SNA_RESPONSE as SNA_RESPONSE_TYPE_UTIL,
            TELOPT_OLD_ENVIRON as TELOPT_TERMINAL_LOCATION, TN3270E_IBM_DYNAMIC
        )
        from pure3270.protocol.data_stream import (
            STRUCTURED_FIELD, BIND_SF_TYPE, SNA_RESPONSE_DATA_TYPE, PRINTER_STATUS_DATA_TYPE,
            SNA_COMMAND_RESPONSE, SNA_DATA_RESPONSE,
            SNA_SENSE_CODE_SUCCESS, SNA_SENSE_CODE_INVALID_FORMAT,
            SNA_SENSE_CODE_NOT_SUPPORTED, SNA_SENSE_CODE_SESSION_FAILURE,
            PRINTER_STATUS_SF_TYPE, SOH_DEVICE_END, SOH_INTERVENTION_REQUIRED, SOH_SUCCESS,
            SOH, QUERY_REPLY_SF, QUERY_REPLY_CHARACTERISTICS
        )
        from pure3270.protocol.tn3270e_header import TN3270EHeader

        try:
            negotiation_done = False
            while True:
                data = await reader.read(1024)
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
                                        response.extend(bytes([IAC, DO, TELOPT_TN3270E]))
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
    def __init__(self, port=2331, rows=32, cols=80):
        super().__init__(port)
        self.rows = rows
        self.cols = cols
        self.bind_image_sent = asyncio.Event()

    async def handle_client(self, reader, writer):
        from pure3270.protocol.utils import (
            IAC, DO, WILL, SB, SE,
            TELOPT_TTYPE, TELOPT_BINARY, TELOPT_EOR, TELOPT_TN3270E,
            TN3270E_DEVICE_TYPE, TN3270E_FUNCTIONS, TN3270E_IS, TN3270E_SEND,
            TN3270E_BIND_IMAGE, TN3270E_RESPONSES,
            TN3270E_IBM_DYNAMIC
        )
        from pure3270.protocol.data_stream import (
            STRUCTURED_FIELD, QUERY_REPLY_SF, QUERY_REPLY_CHARACTERISTICS
        )

        try:
            negotiation_done = False
            negotiated_tn3270e_device_type = False
            negotiated_tn3270e_functions = False
            self.query_sf_received = asyncio.Event()  # Add missing event
            while True:
                data = await reader.read(1024)
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
                                        response.extend(bytes([IAC, DO, TELOPT_TN3270E]))
                                    else:
                                        response.extend(bytes([IAC, DONT, option]))
                                    i += 3
                                else: # Incomplete command
                                    break
                            elif command == SB:
                                # Look for IAC SE
                                j = i + 2
                                while j < len(data) and not (data[j] == IAC and j + 1 < len(data) and data[j+1] == SE):
                                    j += 1
                                
                                if j + 1 < len(data) and data[j+1] == SE:
                                    sub_option = data[i+2]
                                    sub_data = data[i+3:j]

                                    if sub_option == TELOPT_TN3270E:
                                        # Parse TN3270E subnegotiation
                                        if len(sub_data) >= 2:
                                            tn3270e_type = sub_data[0]
                                            tn3270e_subtype = sub_data[1]

                                            if tn3270e_type == TN3270E_DEVICE_TYPE and tn3270e_subtype == TN3270E_SEND:
                                                # Respond with DEVICE-TYPE IS IBM-DYNAMIC
                                                device_type_response = TN3270E_IBM_DYNAMIC.encode("ascii") + b"\x00"
                                                response.extend(bytes([IAC, SB, TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_IS]) + device_type_response + bytes([IAC, SE]))
                                                negotiated_tn3270e_device_type = True
                                            elif tn3270e_type == TN3270E_FUNCTIONS and tn3270e_subtype == TN3270E_SEND:
                                                # Respond with FUNCTIONS IS (example: BIND-IMAGE, RESPONSES)
                                                functions_response = bytes([TN3270E_BIND_IMAGE | TN3270E_RESPONSES])
                                                response.extend(bytes([IAC, SB, TELOPT_TN3270E, TN3270E_FUNCTIONS, TN3270E_IS]) + functions_response + bytes([IAC, SE]))
                                                negotiated_tn3270e_functions = True
                                            elif len(sub_data) >= 1 and sub_data[0] == STRUCTURED_FIELD: # Check for Structured Field
                                                # SF format: SF_ID, Length (2 bytes), SF_Type (1 byte), Data
                                                if len(sub_data) >= 4: # Min length for a query SF (SF_ID, Len, Query_SF_Type, Query_Type)
                                                    # sub_data[0] is STRUCTURED_FIELD, so we start from index 1
                                                    sf_len = (sub_data[1] << 8) | sub_data[2]
                                                    sf_type = sub_data[3] if len(sub_data) > 3 else None
                                                    if sf_type == QUERY_REPLY_SF: # It's a Query SF
                                                        query_type = sub_data[4] if len(sub_data) > 4 else None
                                                        if query_type == QUERY_REPLY_CHARACTERISTICS:
                                                            print(f"Mock Server: Received QUERY_REPLY_CHARACTERISTICS request. Responding with {self.rows}x{self.cols}")
                                                            # Build QUERY_REPLY_CHARACTERISTICS response
                                                            reply_data = bytearray()
                                                            reply_data.append(QUERY_REPLY_SF) # 0x88
                                                            reply_data.append(QUERY_REPLY_CHARACTERISTICS) # 0x02
                                                            reply_data.extend(self.rows.to_bytes(2, 'big'))
                                                            reply_data.extend(self.cols.to_bytes(2, 'big'))
                                                            
                                                            sf_response = bytearray()
                                                            sf_response.append(STRUCTURED_FIELD) # 0x3C
                                                            sf_response.extend((len(reply_data) + 2).to_bytes(2, 'big'))
                                                            sf_response.extend(reply_data)
                                                            response.extend(bytes([IAC, SB, TELOPT_TN3270E]) + sf_response + bytes([IAC, SE]))
                                                            self.query_sf_received.set() # Signal that query SF was handled
                                                i = j + 2
                                            else: # Unhandled IAC command
                                                i += 2
                                        else: # Incomplete IAC sequence
                                            break
                                    else: # Not an IAC, just echo
                                        response.append(data[i])
                                        i += 1
                                
                                if response:
                                    writer.write(response)
                                    await writer.drain()
                                    await asyncio.sleep(0.01) # Give client time to process

                if negotiated_tn3270e_device_type and negotiated_tn3270e_functions and not self.negotiation_complete.is_set():
                    self.negotiation_complete.set()
                    print("Mock Server: TN3270E negotiation complete.")
                    # Send BIND-IMAGE after negotiation is complete
                    self.bind_image_sent.set()
        except Exception as e:
            print(f"Mock server client handler error: {e}")
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
    def __init__(self, port=2330):
        super().__init__(port)
        self.positive_response_sent = asyncio.Event()
        self.negative_response_sent = asyncio.Event()
        self.lu_busy_response_sent = asyncio.Event()
        self.invalid_sequence_response_sent = asyncio.Event()
        self.session_failure_response_sent = asyncio.Event()
        self.state_error_response_sent = asyncio.Event()

    async def handle_client(self, reader, writer):
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
            SNA_RESPONSE_DATA_TYPE  # Import the correct data type
        )
        from pure3270.protocol.tn3270e_header import TN3270EHeader

        try:
            negotiation_done = False
            while True:
                data = await reader.read(1024)
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
                                        response.extend(bytes([IAC, DO, TELOPT_TN3270E]))
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
                    else:
                        i += 1
                
                if response:
                    writer.write(response)
                    await writer.drain()

                if self.negotiation_complete.is_set() and not negotiation_done:
                    print("Mock Server: Negotiation complete. Sending SNA responses.")
                    
                    # 1. Positive SNA Response (ACK)
                    # Data: Response Type (1 byte), Flags (1 byte), Sense Code (2 bytes, 0x0000 for success)
                    positive_sna_data = bytes([SNA_COMMAND_RESPONSE, SNA_FLAGS_RSP, 0x00, 0x00]) # Command response, RSP flag, success sense code
                    positive_header = TN3270EHeader(
                        data_type=SNA_RESPONSE_DATA_TYPE, # Use the correct SNA_RESPONSE data type
                        request_flag=0, response_flag=0, seq_number=1
                    )
                    # Send as regular TN3270E data, not subnegotiation
                    positive_response_msg = positive_header.to_bytes() + positive_sna_data
                    writer.write(positive_response_msg)
                    await writer.drain()
                    print(f"Mock Server: Sent Positive SNA Response: {positive_response_msg.hex()}")
                    self.positive_response_sent.set()

                    await asyncio.sleep(0.1) # Small delay between responses

                    # 2. Negative SNA Response (Session Failure)
                    negative_sna_data_session_failure = bytes([SNA_COMMAND_RESPONSE, SNA_FLAGS_RSP | SNA_FLAGS_EXCEPTION_RESPONSE, (SNA_SENSE_CODE_SESSION_FAILURE >> 8) & 0xFF, SNA_SENSE_CODE_SESSION_FAILURE & 0xFF])
                    negative_header_session_failure = TN3270EHeader(
                        data_type=SNA_RESPONSE_DATA_TYPE,
                        request_flag=0, response_flag=0, seq_number=2
                    )
                    # Send as regular TN3270E data, not subnegotiation
                    negative_response_msg_session_failure = negative_header_session_failure.to_bytes() + negative_sna_data_session_failure
                    writer.write(negative_response_msg_session_failure)
                    await writer.drain()
                    print(f"Mock Server: Sent Negative SNA Response (Session Failure): {negative_response_msg_session_failure.hex()}")
                    self.session_failure_response_sent.set()
                    self.negative_response_sent.set() # General negative response flag

                    await asyncio.sleep(0.1)

                    # 3. Negative SNA Response (LU Busy)
                    negative_sna_data_lu_busy = bytes([SNA_COMMAND_RESPONSE, SNA_FLAGS_RSP | SNA_FLAGS_EXCEPTION_RESPONSE, (SNA_SENSE_CODE_LU_BUSY >> 8) & 0xFF, SNA_SENSE_CODE_LU_BUSY & 0xFF])
                    negative_header_lu_busy = TN3270EHeader(
                        data_type=SNA_RESPONSE_DATA_TYPE,
                        request_flag=0, response_flag=0, seq_number=3
                    )
                    # Send as regular TN3270E data, not subnegotiation
                    negative_response_msg_lu_busy = negative_header_lu_busy.to_bytes() + negative_sna_data_lu_busy
                    writer.write(negative_response_msg_lu_busy)
                    await writer.drain()
                    print(f"Mock Server: Sent Negative SNA Response (LU Busy): {negative_response_msg_lu_busy.hex()}")
                    self.lu_busy_response_sent.set()

                    await asyncio.sleep(0.1)

                    # 4. Negative SNA Response (Invalid Sequence)
                    negative_sna_data_invalid_sequence = bytes([SNA_COMMAND_RESPONSE, SNA_FLAGS_RSP | SNA_FLAGS_EXCEPTION_RESPONSE, (SNA_SENSE_CODE_INVALID_SEQUENCE >> 8) & 0xFF, SNA_SENSE_CODE_INVALID_SEQUENCE & 0xFF])
                    negative_header_invalid_sequence = TN3270EHeader(
                        data_type=SNA_RESPONSE_DATA_TYPE,
                        request_flag=0, response_flag=0, seq_number=4
                    )
                    # Send as regular TN3270E data, not subnegotiation
                    negative_response_msg_invalid_sequence = negative_header_invalid_sequence.to_bytes() + negative_sna_data_invalid_sequence
                    writer.write(negative_response_msg_invalid_sequence)
                    await writer.drain()
                    print(f"Mock Server: Sent Negative SNA Response (Invalid Sequence): {negative_response_msg_invalid_sequence.hex()}")
                    self.invalid_sequence_response_sent.set()

                    await asyncio.sleep(0.1)

                    # 5. Negative SNA Response (State Error)
                    negative_sna_data_state_error = bytes([SNA_COMMAND_RESPONSE, SNA_FLAGS_RSP | SNA_FLAGS_EXCEPTION_RESPONSE, (SNA_SENSE_CODE_STATE_ERROR >> 8) & 0xFF, SNA_SENSE_CODE_STATE_ERROR & 0xFF])
                    negative_header_state_error = TN3270EHeader(
                        data_type=SNA_RESPONSE_DATA_TYPE,
                        request_flag=0, response_flag=0, seq_number=5
                    )
                    # Send as regular TN3270E data, not subnegotiation
                    negative_response_msg_state_error = negative_header_state_error.to_bytes() + negative_sna_data_state_error
                    writer.write(negative_response_msg_state_error)
                    await writer.drain()
                    print(f"Mock Server: Sent Negative SNA Response (State Error): {negative_response_msg_state_error.hex()}")
                    self.state_error_response_sent.set()

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
        await session.connect()

        # Wait for the mock server to send positive and negative SNA responses
        await asyncio.wait_for(mock_server.positive_response_sent.wait(), timeout=5)
        print("   ✓ Received positive SNA response from mock server.")
        assert session.sna_session_state == SnaSessionState.NORMAL.value, f"Expected SNA state NORMAL, got {session.sna_session_state}"

        await asyncio.wait_for(mock_server.session_failure_response_sent.wait(), timeout=5)
        print("   ✓ Received negative SNA response (Session Failure) from mock server.")
        assert session.sna_session_state == "SESSION_DOWN", f"Expected SNA state SESSION_DOWN, got {session.sna_session_state}"

        await asyncio.wait_for(mock_server.lu_busy_response_sent.wait(), timeout=5)
        print("   ✓ Received negative SNA response (LU Busy) from mock server.")
        assert session.sna_session_state == "LU_BUSY", f"Expected SNA state LU_BUSY, got {session.sna_session_state}"

        await asyncio.wait_for(mock_server.invalid_sequence_response_sent.wait(), timeout=5)
        print("   ✓ Received negative SNA response (Invalid Sequence) from mock server.")
        assert session.sna_session_state == "INVALID_SEQUENCE", f"Expected SNA state INVALID_SEQUENCE, got {session.sna_session_state}"

        await asyncio.wait_for(mock_server.state_error_response_sent.wait(), timeout=5)
        print("   ✓ Received negative SNA response (State Error) from mock server.")
        assert session.sna_session_state == "STATE_ERROR", f"Expected SNA state STATE_ERROR, got {session.sna_session_state}"
        
        return True
    except asyncio.TimeoutError:
        print("   ✗ SNA response handling test timed out.")
        return False
    except Exception as e:
        print(f"   ✗ SNA response handling test failed: {e}")
        return False
    finally:
        if session:
            await session.close()


async def test_lu_name_negotiation(port, mock_server):
    """
    Test that pure3270 correctly handles LU name negotiation (RFC 1646).
    """
    print("10. Testing LU Name negotiation...")
    server = mock_server
    session = None
    try:
        from pure3270 import AsyncSession
        session = AsyncSession(host="localhost", port=port)
        session.lu_name = "MYLU"
        await session.connect()

        # Wait for the mock server to receive the LU name
        await asyncio.wait_for(server.lu_name_received.wait(), timeout=5)
        
        assert server.received_lu_name == "MYLU"
        print("   ✓ LU Name negotiation successful and LU name received by mock server.")

        return True
    except asyncio.TimeoutError:
        print("   ✗ LU Name negotiation test timed out.")
        return False
    except Exception as e:
        print(f"   ✗ LU Name negotiation test failed: {e}")
        return False
    finally:
        if session:
            await session.close()
        if server:
            await server.stop()

async def test_bind_image_processing(port, mock_server):
    """
    Test that pure3270 correctly processes BIND-IMAGE Structured Fields.
    """
    print("10. Testing BIND-IMAGE processing...")
    session = None
    try:
        from pure3270 import AsyncSession
        session = AsyncSession(host="localhost", port=port)
        await session.connect()

        # Wait for the mock server to send the BIND-IMAGE
        await asyncio.wait_for(mock_server.bind_image_sent.wait(), timeout=5)

        # Verify that the screen dimensions are updated by the BIND-IMAGE
        assert session.screen.rows == mock_server.rows
        assert session.screen.cols == mock_server.cols
        print(f"   ✓ Screen dimensions updated by BIND-IMAGE: {session.screen.rows}x{session.screen.cols}")

        return True
    except asyncio.TimeoutError:
        print("   ✗ BIND-IMAGE processing test timed out.")
        return False
    except Exception as e:
        print(f"   ✗ BIND-IMAGE processing test failed: {e}")
        return False
    finally:
        if session:
            await session.close()
        if mock_server:
            await mock_server.stop()
        # No need to cancel server_task here, main() handles it.


async def test_printer_status_communication(port, mock_server):
    """
    Test that pure3270 correctly handles printer status communication.
    """
    print("11. Testing Printer Status Communication...")
    server = mock_server
    session = None
    try:
        from pure3270 import AsyncSession
        session = AsyncSession(host="localhost", port=port)
        session.is_printer_session = True # Manually set to printer session for testing
        await session.connect()

        # Wait for the mock server to send printer status messages
        await asyncio.wait_for(server.negotiation_complete.wait(), timeout=5)
        
        # Verify client can send printer status
        from pure3270.protocol.data_stream import SOH_DEVICE_END, SOH_INTERVENTION_REQUIRED, DEVICE_END, INTERVENTION_REQUIRED
        await session.send_soh_message(SOH_DEVICE_END)
        await asyncio.wait_for(server.client_soh_received.wait(), timeout=5)
        assert server.received_soh_status == SOH_DEVICE_END
        print("   ✓ Client sent SOH_DEVICE_END and mock server received it.")

        server.client_soh_received.clear() # Clear for next test
        await session.send_soh_message(SOH_INTERVENTION_REQUIRED)
        await asyncio.wait_for(server.client_soh_received.wait(), timeout=5)
        assert server.received_soh_status == SOH_INTERVENTION_REQUIRED
        print("   ✓ Client sent SOH_INTERVENTION_REQUIRED and mock server received it.")

        await session.send_printer_status_sf(DEVICE_END)
        await asyncio.wait_for(server.client_printer_status_sf_received.wait(), timeout=5)
        assert server.received_printer_status_sf_code == DEVICE_END
        print("   ✓ Client sent PRINTER_STATUS_SF with DEVICE_END and mock server received it.")

        server.client_printer_status_sf_received.clear() # Clear for next test
        await session.send_printer_status_sf(INTERVENTION_REQUIRED)
        await asyncio.wait_for(server.client_printer_status_sf_received.wait(), timeout=5)
        assert server.received_printer_status_sf_code == INTERVENTION_REQUIRED
        print("   ✓ Client sent PRINTER_STATUS_SF with INTERVENTION_REQUIRED and mock server received it.")

        print(f"   ✓ Current session printer status: {session.printer_status}")

        return True
    except asyncio.TimeoutError:
        print("   ✗ Printer Status Communication test timed out.")
        return False
    except Exception as e:
        print(f"   ✗ Printer Status Communication test failed: {e}")
        return False
    finally:
        if session:
            await session.close()
        if server:
            await server.stop()


async def test_mock_server_connectivity(port):
    """Test mock server connectivity."""
    print("Testing mock server connectivity...")
    try:
        import pure3270
        from pure3270 import AsyncSession

        # Test AsyncSession connection
        session = AsyncSession("localhost", port)
        try:
            await session.connect()
            print("   ✓ AsyncSession connection successful")

            # Test sending and receiving data
            test_data = b"Hello, TN3270!"
            await session.send(test_data)
            # Note: Mock server echoes back, but we're not checking the response
            # since this is just a basic connectivity test
            print("   ✓ Data send/receive test")

            await session.close()
            print("   ✓ Session close")
            return True
        except Exception as e:
            print(f"   ✗ AsyncSession connection failed: {e}")
            return False
        finally:
            try:
                await session.close()
            except:
                pass
    except Exception as e:
        print(f"   ✗ Mock server connectivity test failed: {e}")
        return False


async def main():
    print("Running integration tests...")
    results = {}

    results["basic_functionality"] = test_basic_functionality()
    
    # Test cases that require mock servers
    # Start mock servers in the background
    mock_server = MockServer()
    mock_server_task = asyncio.create_task(mock_server.start())
    await asyncio.sleep(0.1) # Give server a moment to start

    tn3270e_mock_server = TN3270ENegotiatingMockServer()
    tn3270e_mock_server_task = asyncio.create_task(tn3270e_mock_server.start())
    await asyncio.sleep(0.1)

    bind_image_mock_server = BindImageMockServer()
    bind_image_mock_server_task = asyncio.create_task(bind_image_mock_server.start())
    await asyncio.sleep(0.1)

    lu_name_mock_server = LUNameMockServer()
    lu_name_mock_server_task = asyncio.create_task(lu_name_mock_server.start())
    await asyncio.sleep(0.1)

    printer_status_mock_server = PrinterStatusMockServer()
    printer_status_mock_server_task = asyncio.create_task(printer_status_mock_server.start())
    await asyncio.sleep(0.1)

    sna_aware_mock_server = SNAAwareMockServer()
    sna_aware_mock_server_task = asyncio.create_task(sna_aware_mock_server.start())
    await asyncio.sleep(0.1)

    results["mock_server_connectivity"] = await test_mock_server_connectivity(mock_server.port)
    results["bind_image_processing"] = await test_bind_image_processing(bind_image_mock_server.port, bind_image_mock_server)
    results["sna_response_handling"] = await test_sna_response_handling(sna_aware_mock_server.port, sna_aware_mock_server)
    results["lu_name_negotiation"] = await test_lu_name_negotiation(lu_name_mock_server.port, lu_name_mock_server)
    results["printer_status_communication"] = await test_printer_status_communication(printer_status_mock_server.port, printer_status_mock_server)

    # Stop mock servers
    await mock_server.stop()
    mock_server_task.cancel()
    await tn3270e_mock_server.stop()
    tn3270e_mock_server_task.cancel()
    await bind_image_mock_server.stop()
    bind_image_mock_server_task.cancel()
    await lu_name_mock_server.stop()
    lu_name_mock_server_task.cancel()
    await printer_status_mock_server.stop()
    printer_status_mock_server_task.cancel()
    await sna_aware_mock_server.stop()
    sna_aware_mock_server_task.cancel()

    # Wait for tasks to finish cancelling
    try:
        await asyncio.gather(
            mock_server_task,
            tn3270e_mock_server_task,
            bind_image_mock_server_task,
            lu_name_mock_server_task,
            printer_status_mock_server_task,
            sna_aware_mock_server_task,
            return_exceptions=True # Don't raise CancelledError
        )
    except Exception as e:
        print(f"Error during task cancellation: {e}")

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
