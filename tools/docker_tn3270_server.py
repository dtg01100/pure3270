#!/usr/bin/env python3
"""
Docker TN3270 Server for Testing

This script creates a lightweight TN3270 test server using Docker.
Provides a reproducible, isolated testing environment.

Usage:
    python tools/docker_tn3270_server.py --start
    python examples/test_real_server.py --mode mock --port 9923
    python tools/docker_tn3270_server.py --stop

Requirements:
    - Docker installed and running
    - Permissions to run Docker containers

Docker Image Options:
    - tn3270/test-server - Basic TN3270 server
    - tn3270/linux-mainframe - Linux with TN3270 emulator
    - ibmcom/ibmq - IBM MQ with TN3270 (commercial)

For development testing, we use a minimal TN3270 simulator.
"""

import argparse
import logging
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DockerContainer:
    """Represents a Docker container running TN3270 server."""

    id: str
    name: str
    port: int
    status: str


def check_docker_available() -> bool:
    """Check if Docker is available and running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def pull_image(image: str) -> bool:
    """Pull Docker image for TN3270 server."""
    logger.info(f"Pulling image: {image}")
    try:
        result = subprocess.run(
            ["docker", "pull", image],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Failed to pull image: {e}")
        return False


def start_tn3270_container(
    image: str = "e老大/tn3270:latest",
    port: int = 9923,
    name: str = "pure3270-test-server",
) -> Optional[DockerContainer]:
    """
    Start a TN3270 Docker container.

    Note: This uses a mock TN3270 server for testing.
    For real mainframe testing, you would use actual TN3270 server images.
    """
    # Check if container already exists
    existing = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name={name}", "--format", "{{.ID}}"],
        capture_output=True,
        text=True,
    )
    if existing.stdout.strip():
        logger.info(f"Removing existing container: {name}")
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)

    # Create a simple TN3270 mock server Dockerfile
    dockerfile_content = """
FROM python:3.11-slim

WORKDIR /app

# Install asyncio-based TN3270 server
RUN echo '
import asyncio
import struct

async def handle_client(reader, writer):
    addr = writer.get_extra_info("peername")
    print(f"Connection from {addr}")

    # TN3270 negotiation
    writer.write(b"\\xff\\xfb\\x19")  # WILL EOR
    await writer.drain()

    # Send welcome screen
    welcome = bytearray()
    welcome.extend([0xf5, 0xc3])  # Erase/Write, WCC
    welcome.extend(b"Welcome to Pure3270 Test Server")
    writer.write(bytes(welcome))
    writer.write(b"\\xff\\xef")  # IAC EOR
    await writer.drain()

    await asyncio.sleep(0.5)
    writer.close()

async def main():
    server = await asyncio.start_server(handle_client, "0.0.0.0", 9923)
    print("TN3270 server running on port 9923")
    async with server:
        await server.serve_forever()

asyncio.run(main())
' > server.py

CMD ["python", "server.py"]
"""

    # Write Dockerfile to temp location
    dockerfile_path = Path(
        "/tmp/tn3270-test-docker"
    )  # nosec: B108 - test fixture, not production
    dockerfile_path.mkdir(exist_ok=True)
    (dockerfile_path / "Dockerfile").write_text(dockerfile_content)

    # Build image
    logger.info("Building TN3270 test server image...")
    build_result = subprocess.run(
        ["docker", "build", "-t", "pure3270-test-server", str(dockerfile_path)],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if build_result.returncode != 0:
        logger.error(f"Build failed: {build_result.stderr}")
        return None

    # Run container
    logger.info(f"Starting container on port {port}...")
    run_result = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "-p",
            f"{port}:9923",
            "pure3270-test-server",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if run_result.returncode != 0:
        logger.error(f"Failed to start container: {run_result.stderr}")
        return None

    container_id = run_result.stdout.strip()

    # Wait for container to be running
    time.sleep(2)

    return DockerContainer(
        id=container_id,
        name=name,
        port=port,
        status="running",
    )


def stop_container(name: str = "pure3270-test-server") -> bool:
    """Stop and remove the TN3270 test container."""
    try:
        subprocess.run(
            ["docker", "stop", name],
            capture_output=True,
            timeout=30,
        )
        subprocess.run(
            ["docker", "rm", name],
            capture_output=True,
        )
        logger.info(f"Container '{name}' stopped and removed")
        return True
    except Exception as e:
        logger.error(f"Failed to stop container: {e}")
        return False


def get_container_status(
    name: str = "pure3270-test-server",
) -> Optional[DockerContainer]:
    """Get status of the TN3270 test container."""
    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                f"name={name}",
                "--format",
                "{{.ID}}|{{.Status}}",
            ],
            capture_output=True,
            text=True,
        )

        if result.stdout.strip():
            parts = result.stdout.strip().split("|")
            return DockerContainer(
                id=parts[0],
                name=name,
                port=9923,  # Default port
                status=parts[1] if len(parts) > 1 else "unknown",
            )
    except Exception:
        pass

    return None


def test_container_connectivity(container: DockerContainer) -> bool:
    """Test if we can connect to the containerized TN3270 server."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(("127.0.0.1", container.port))

        data = sock.recv(256)
        sock.close()

        logger.info(f"Received {len(data)} bytes from container")
        return len(data) > 0
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Docker-based TN3270 server for testing"
    )
    parser.add_argument("--start", action="store_true", help="Start TN3270 test server")
    parser.add_argument("--stop", action="store_true", help="Stop TN3270 test server")
    parser.add_argument("--status", action="store_true", help="Show container status")
    parser.add_argument("--port", type=int, default=9923, help="Port for TN3270 server")
    parser.add_argument("--name", default="pure3270-test-server", help="Container name")
    parser.add_argument("--test", action="store_true", help="Test connectivity")

    args = parser.parse_args()

    # Check Docker availability
    if not check_docker_available():
        logger.error("Docker is not available or not running")
        logger.info("Install Docker: https://docs.docker.com/get-docker/")
        logger.info("Then ensure the Docker daemon is running")
        return 1

    if args.start:
        logger.info("=" * 60)
        logger.info("Starting Docker TN3270 test server")
        logger.info("=" * 60)

        container = start_tn3270_container(port=args.port, name=args.name)
        if container:
            logger.info(f"✓ Container started: {container.id}")
            logger.info(f"  Name: {container.name}")
            logger.info(f"  Port: {container.port}")

            # Test connectivity
            if test_container_connectivity(container):
                logger.info("✓ Container is responding to connections")
                return 0
            else:
                logger.warning("⚠ Container started but not responding")
                return 1
        else:
            logger.error("✗ Failed to start container")
            return 1

    elif args.stop:
        logger.info("=" * 60)
        logger.info("Stopping Docker TN3270 test server")
        logger.info("=" * 60)

        if stop_container(args.name):
            logger.info("✓ Container stopped successfully")
            return 0
        else:
            logger.error("✗ Failed to stop container")
            return 1

    elif args.status:
        container = get_container_status(args.name)
        if container:
            logger.info(f"Container: {container.name}")
            logger.info(f"  ID: {container.id}")
            logger.info(f"  Status: {container.status}")
            logger.info(f"  Port: {container.port}")
        else:
            logger.info(f"Container '{args.name}' is not running")
        return 0

    elif args.test:
        container = get_container_status(args.name)
        if container:
            if test_container_connectivity(container):
                logger.info("✓ Container is reachable")
                return 0
            else:
                logger.error("✗ Container is not responding")
                return 1
        else:
            logger.error("No container running")
            return 1

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
