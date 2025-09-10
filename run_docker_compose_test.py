#!/usr/bin/env python3
"""
Simple test script to demonstrate Docker Compose-based testing.
This script can be used in CI/CD pipelines.
"""

import subprocess
import sys
import time

def run_docker_compose_test():
    """Run tests using Docker Compose."""
    try:
        # Start services
        print("Starting Docker Compose services...")
        result = subprocess.run([
            "docker-compose", "-f", "docker-compose.test.yml", "up", "-d"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Failed to start services: {result.stderr}")
            return False
        
        print("Services started successfully")
        
        # Wait for services to be ready
        print("Waiting for services to initialize...")
        time.sleep(10)
        
        # Run integration tests
        print("Running integration tests...")
        result = subprocess.run([
            "python", "refined_docker_integration_test.py"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error running Docker Compose test: {e}")
        return False
    finally:
        # Clean up
        print("Cleaning up Docker Compose services...")
        subprocess.run([
            "docker-compose", "-f", "docker-compose.test.yml", "down"
        ], capture_output=True)

if __name__ == "__main__":
    success = run_docker_compose_test()
    sys.exit(0 if success else 1)