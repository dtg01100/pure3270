#!/usr/bin/env python3
"""
Mock TN3270 server for integration testing.
"""

import asyncio
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockTN3270Server:
    """Mock TN3270 server for testing purposes."""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 23):
        self.host = host
        self.port = port
        self.server: Optional[asyncio.Server] = None
        self.clients = []
        
    async def start(self):
        """Start the mock server."""
        self.server = await asyncio.start_server(
            self.handle_client, 
            self.host, 
            self.port
        )
        logger.info(f"Mock TN3270 server started on {self.host}:{self.port}")
        return self.server
        
    async def handle_client(self, reader, writer):
        """Handle a client connection."""
        addr = writer.get_extra_info('peername')
        logger.info(f"Client connected from {addr}")
        self.clients.append((reader, writer))
        
        try:
            # Send initial negotiation sequence
            await self.send_initial_negotiation(writer)
            
            # Main communication loop
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                    
                logger.info(f"Received from client: {data.hex()}")
                await self.handle_client_data(data, writer)
                
        except Exception as e:
            logger.error(f"Error handling client {addr}: {e}")
        finally:
            logger.info(f"Client {addr} disconnected")
            self.clients.remove((reader, writer))
            writer.close()
            await writer.wait_closed()
            
    async def send_initial_negotiation(self, writer):
        """Send initial TN3270 negotiation sequence."""
        # This is a simplified example - real TN3270 negotiation is more complex
        # Send DO TERMINAL TYPE
        writer.write(b'\xff\xfd\x18')
        await writer.drain()
        
    async def handle_client_data(self, data, writer):
        """Handle data received from client."""
        # Echo data back for testing
        writer.write(data)
        await writer.drain()
        
    async def stop(self):
        """Stop the mock server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("Mock TN3270 server stopped")

# Example usage
async def main():
    server = MockTN3270Server()
    try:
        await server.start()
        # Keep server running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    finally:
        await server.stop()

if __name__ == "__main__":
    asyncio.run(main())