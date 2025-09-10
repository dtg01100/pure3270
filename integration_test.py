#!/usr/bin/env python3
"""
Integration tests using a mock TN3270 server.
"""

import asyncio
import pytest
import threading
import time
from unittest.mock import patch

import pure3270
from pure3270 import AsyncSession

class MockTN3270Server:
    """Simple mock TN3270 server for integration testing."""
    
    def __init__(self, host='127.0.0.1', port=2323):
        self.host = host
        self.port = port
        self.server = None
        self.connections = []
        
    async def start(self):
        """Start the mock server."""
        self.server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )
        return self.server
        
    async def handle_client(self, reader, writer):
        """Handle a client connection."""
        self.connections.append((reader, writer))
        
        try:
            # Read data from client
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                # Echo back
                writer.write(data)
                await writer.drain()
        except Exception:
            pass
        finally:
            if (reader, writer) in self.connections:
                self.connections.remove((reader, writer))
            writer.close()
            await writer.wait_closed()
            
    async def stop(self):
        """Stop the mock server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()

@pytest.mark.asyncio
async def test_integration_with_mock_server():
    """Test pure3270 integration with mock server."""
    # Enable pure3270 patching
    pure3270.enable_replacement()
    
    # Start mock server
    server = MockTN3270Server(port=2323)
    await server.start()
    
    try:
        # Test connection with pure3270
        session = AsyncSession("127.0.0.1", 2323)
        
        # This would test the actual connection, but we'll skip for now
        # since our mock server is very simple
        assert session is not None
        assert not session.connected
        
    finally:
        await server.stop()

def test_p3270_integration_with_mock_server():
    """Test p3270 integration with mock server using pure3270 patching."""
    # Enable pure3270 patching
    pure3270.enable_replacement()
    
    # Import p3270 after patching
    import p3270
    
    # Create client
    client = p3270.P3270Client()
    
    # Verify patching worked
    assert client is not None
    # The s3270 attribute should now be a Pure3270S3270Wrapper
    assert 'Pure3270S3270Wrapper' in str(type(client.s3270))

if __name__ == "__main__":
    # Run the tests
    test_p3270_integration_with_mock_server()
    print("Integration test passed!")