#!/usr/bin/env python3
"""
Test script to run a Hercules-based TN3270 server in Docker and test against it.
Hercules acts as a TN3270 server that pure3270 can connect to as a client.
"""

import docker
import time
import subprocess
import threading
import requests
from typing import Optional

class HerculesTestEnvironment:
    """Test environment using a Hercules-based mainframe emulator as TN3270 server."""
    
    def __init__(self):
        self.client = docker.from_env()
        self.container: Optional[docker.models.containers.Container] = None
        self.container_name = "test-hercules-mainframe"
        
    def start_hercules(self):
        """Start a Hercules mainframe emulator (TN3270 server) in Docker."""
        try:
            # Try to remove any existing container with the same name
            try:
                old_container = self.client.containers.get(self.container_name)
                old_container.remove(force=True)
                print(f"Removed existing container: {self.container_name}")
            except docker.errors.NotFound:
                pass
            
            # Start the Hercules container (acts as TN3270 server)
            print("Starting Hercules mainframe emulator (TN3270 server)...")
            self.container = self.client.containers.run(
                "mainframed767/hercules:latest",
                name=self.container_name,
                detach=True,
                ports={
                    '23/tcp': 2323,  # Map TN3270 port to 2323
                    '80/tcp': 8080,  # Map HTTP port if available
                },
                # Remove the container when stopped
                remove=True
            )
            
            print(f"Hercules TN3270 server container started: {self.container.id}")
            
            # Wait for the container to be ready
            timeout = 60  # 60 seconds timeout
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    # Check if container is running
                    self.container.reload()
                    if self.container.status == 'running':
                        print("Container is running, waiting for TN3270 services to start...")
                        time.sleep(10)  # Give services time to start
                        return True
                except Exception as e:
                    print(f"Error checking container status: {e}")
                
                time.sleep(2)
            
            print("Timeout waiting for container to be ready")
            return False
            
        except Exception as e:
            print(f"Error starting Hercules TN3270 server container: {e}")
            return False
    
    def test_connection(self):
        """Test connection to the TN3270 server."""
        try:
            # Test if we can connect to the TN3270 port
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('localhost', 2323))
            sock.close()
            
            if result == 0:
                print("✓ Successfully connected to TN3270 server on port 2323")
                return True
            else:
                print("✗ Could not connect to TN3270 server on port 2323")
                return False
                
        except Exception as e:
            print(f"Error testing connection: {e}")
            return False
    
    def stop_hercules(self):
        """Stop the Hercules container."""
        if self.container:
            try:
                print("Stopping Hercules TN3270 server container...")
                self.container.stop(timeout=10)
                print("Hercules TN3270 server container stopped")
            except Exception as e:
                print(f"Error stopping container: {e}")
    
    def run_pure3270_test(self):
        """Run pure3270 tests against the Hercules TN3270 server."""
        try:
            # Import pure3270
            import pure3270
            from pure3270 import AsyncSession
            
            # Enable patching for p3270 tests
            pure3270.enable_replacement()
            import p3270
            
            print("Testing pure3270 connection to Hercules TN3270 server...")
            
            # Test with AsyncSession (pure3270 client connecting to Hercules server)
            async def test_async_connection():
                session = AsyncSession("localhost", 2323)
                try:
                    await session.connect()
                    print("✓ AsyncSession connected successfully to Hercules TN3270 server")
                    await session.close()
                    return True
                except Exception as e:
                    print(f"✗ AsyncSession connection failed: {e}")
                    return False
            
            # Test with p3270 (patched to use pure3270)
            def test_p3270_connection():
                try:
                    client = p3270.P3270Client()
                    print("✓ p3270 client created with pure3270 patching")
                    return True
                except Exception as e:
                    print(f"✗ p3270 client creation failed: {e}")
                    return False
            
            # Run tests
            import asyncio
            result1 = asyncio.run(test_async_connection())
            result2 = test_p3270_connection()
            
            return result1 and result2
            
        except Exception as e:
            print(f"Error running pure3270 tests: {e}")
            return False

def main():
    """Main test function."""
    print("Setting up Hercules-based TN3270 server test environment...")
    print("Hercules acts as the TN3270 server, pure3270 acts as the client.")
    
    # Create test environment
    env = HerculesTestEnvironment()
    
    try:
        # Start Hercules (TN3270 server)
        if not env.start_hercules():
            print("Failed to start Hercules TN3270 server container")
            return False
        
        # Test connection to TN3270 server
        if not env.test_connection():
            print("Failed to connect to TN3270 server")
            return False
        
        # Run pure3270 tests (client connecting to server)
        if not env.run_pure3270_test():
            print("pure3270 tests failed")
            return False
        
        print("\n🎉 All tests passed!")
        return True
        
    except Exception as e:
        print(f"Error during testing: {e}")
        return False
        
    finally:
        # Clean up
        env.stop_hercules()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)