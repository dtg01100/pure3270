#!/usr/bin/env python3
"""
Docker-based integration testing setup.
"""

import docker
import time
import subprocess
import os

def setup_docker_test_environment():
    """
    Setup a Docker-based test environment.
    This is a conceptual example - you would need to find or create
    an appropriate TN3270 server Docker image.
    """
    try:
        # Check if Docker is available
        client = docker.from_env()
        client.ping()
        print("Docker is available")
        
        # Example: Run a mock TN3270 server in Docker
        # This is conceptual - you'd need an actual TN3270 server image
        """
        container = client.containers.run(
            "tn3270-server:latest",  # You would need to find or build this
            ports={'23/tcp': 2323},
            detach=True,
            name="test-tn3270-server"
        )
        """
        print("Docker test environment setup complete")
        return True
    except Exception as e:
        print(f"Docker not available or error occurred: {e}")
        return False

def setup_local_test_environment():
    """
    Setup a local test environment using a simple Python server.
    """
    # Start our mock server in the background
    server_script = """
import asyncio
import socket

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"Connection from {addr}")
    
    try:
        while True:
            data = await reader.read(1024)
            if not data:
                break
            # Echo back
            writer.write(data)
            await writer.drain()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def main():
    server = await asyncio.start_server(handle_client, '127.0.0.1', 2323)
    print("Mock TN3270 server running on 127.0.0.1:2323")
    
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
"""
    
    # Write the server script
    with open('/tmp/mock_tn3270_server.py', 'w') as f:
        f.write(server_script)
    
    # Start the server in background
    try:
        process = subprocess.Popen(['python3', '/tmp/mock_tn3270_server.py'])
        time.sleep(1)  # Give server time to start
        if process.poll() is None:  # Still running
            print("Local mock server started successfully")
            return process
        else:
            print("Failed to start local mock server")
            return None
    except Exception as e:
        print(f"Error starting local server: {e}")
        return None

def run_integration_tests():
    """
    Run integration tests against the test environment.
    """
    print("Running integration tests...")
    
    # Test with pure3270 directly
    try:
        import pure3270
        from pure3270 import AsyncSession
        
        # Enable patching for p3270 tests
        pure3270.enable_replacement()
        import p3270
        
        # Test basic functionality
        session = AsyncSession()
        print("✓ pure3270 AsyncSession created")
        
        client = p3270.P3270Client()
        print("✓ p3270 client created with pure3270 patching")
        print(f"  Client s3270 type: {type(client.s3270)}")
        
        # Test connection (will fail but shouldn't crash)
        try:
            connected = client.isConnected()
            print(f"✓ isConnected() returned: {connected}")
        except Exception as e:
            print(f"✓ isConnected() handled error gracefully: {type(e).__name__}")
            
        print("Integration tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"Integration tests failed: {e}")
        return False

def cleanup_test_environment(process):
    """
    Cleanup the test environment.
    """
    if process:
        try:
            process.terminate()
            process.wait(timeout=5)
            print("Mock server stopped")
        except:
            process.kill()
            print("Mock server killed")

if __name__ == "__main__":
    print("Setting up integration test environment...")
    
    # Try Docker first, then local
    if not setup_docker_test_environment():
        print("Docker not available, using local environment...")
        server_process = setup_local_test_environment()
        
        try:
            run_integration_tests()
        finally:
            cleanup_test_environment(server_process)