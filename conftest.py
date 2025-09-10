"""
pytest configuration for pure3270 integration tests.
"""

import pytest
import docker
import time
import socket
from typing import Optional

class HerculesTestEnvironment:
    """Hercules TN3270 server test environment for pytest."""
    
    def __init__(self):
        self.client = docker.from_env()
        self.container: Optional[docker.models.containers.Container] = None
        self.container_name = "pure3270-pytest-hercules"
        
    def start_hercules(self) -> bool:
        """Start Hercules TN3270 server in Docker for pytest."""
        try:
            # Remove existing container
            try:
                old_container = self.client.containers.get(self.container_name)
                old_container.remove(force=True)
            except docker.errors.NotFound:
                pass
            
            print("Starting Hercules TN3270 server for pytest...")
            
            # Start Hercules container
            self.container = self.client.containers.run(
                "mainframed767/hercules:latest",
                name=self.container_name,
                detach=True,
                ports={
                    '23/tcp': 2380,  # Use port 2380 to avoid conflicts
                },
                # Keep container alive
                command="tail -f /dev/null",
                remove=True
            )
            
            print(f"Hercules container started: {self.container.id[:12]}")
            return True
            
        except Exception as e:
            print(f"Failed to start Hercules container: {e}")
            return False
    
    def wait_for_tn3270_service(self, timeout: int = 120) -> bool:
        """Wait for TN3270 service to become available."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check if container is running
                self.container.reload()
                if self.container.status == 'running':
                    # Test TN3270 port accessibility
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex(('localhost', 2380))
                    sock.close()
                    
                    if result == 0:
                        print("TN3270 service available on port 2380")
                        return True
                    else:
                        print("Waiting for TN3270 service to start...")
                else:
                    print("Container not running")
            except Exception as e:
                print(f"Error checking container: {e}")
            
            time.sleep(5)
        
        print("TN3270 service failed to start in time")
        return False
    
    def stop(self):
        """Stop and cleanup Hercules container."""
        if self.container:
            try:
                print("Stopping Hercules container...")
                self.container.stop(timeout=10)
                print("Hercules container stopped")
            except Exception as e:
                print(f"Error stopping container: {e}")

# Global test environment
hercules_env: Optional[HerculesTestEnvironment] = None

def pytest_addoption(parser):
    """Add custom pytest options."""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests with Hercules TN3270 server"
    )

def pytest_configure(config):
    """Pytest configuration hook - start Hercules environment."""
    global hercules_env
    
    # Only start Hercules if integration tests are requested
    if config.getoption("--integration"):
        print("\n" + "="*60)
        print("STARTING HERCULES TN3270 SERVER FOR INTEGRATION TESTING")
        print("="*60)
        
        hercules_env = HerculesTestEnvironment()
        if hercules_env.start_hercules():
            if hercules_env.wait_for_tn3270_service():
                print("✓ Hercules TN3270 server ready for testing")
            else:
                print("❌ Hercules TN3270 service failed to start")
                hercules_env.stop()
                hercules_env = None
        else:
            print("❌ Failed to start Hercules TN3270 server")
            hercules_env = None

def pytest_unconfigure(config):
    """Pytest unconfigure hook - stop Hercules environment."""
    global hercules_env
    
    if hercules_env:
        print("\n" + "="*60)
        print("STOPPING HERCULES TN3270 SERVER")
        print("="*60)
        hercules_env.stop()
        hercules_env = None

def pytest_collection_modifyitems(config, items):
    """Modify test collection based on options."""
    if not config.getoption("--integration"):
        # Skip integration tests if not requested
        skip_integration = pytest.mark.skip(reason="Need --integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)