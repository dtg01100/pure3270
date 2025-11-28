#!/usr/bin/env python3
"""
Multi-Server Coordinator for Enhanced Testing

Coordinates multiple test servers to simulate complex network environments
and test scenarios that require multiple hosts.

Features:
- Multi-server orchestration
- Load balancing simulation
- Failover testing
- Distributed testing scenarios
- Server health monitoring
- Dynamic server management
"""

import asyncio
import json
import logging
import random
import signal
import socket
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import aiohttp

# Add pure3270 to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class ServerState(Enum):
    """Server states"""

    STARTING = "starting"
    RUNNING = "running"
    STANDBY = "standby"
    FAILED = "failed"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class ServerInstance:
    """Configuration for a server instance"""

    name: str
    host: str
    port: int
    mode: str = "auto"
    weight: int = 1  # For load balancing
    health_check_url: Optional[str] = None
    process: Optional[asyncio.subprocess.Process] = None
    state: ServerState = ServerState.STOPPED
    start_time: Optional[float] = None
    last_health_check: Optional[float] = None
    health_status: bool = False
    connection_count: int = 0
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiServerCoordinator:
    """Coordinates multiple test servers for complex testing scenarios"""

    def __init__(self, config_file: Optional[str] = None):
        self.servers: Dict[str, ServerInstance] = {}
        self.config_file = config_file
        self.coordination_port: int = 2325
        self.health_check_interval: float = 10.0
        self.running = False
        self.load_balancer_enabled = True
        self.failover_enabled = True
        self.server_tasks: Dict[str, asyncio.Task] = {}
        self.health_monitor_task: Optional[asyncio.Task] = None

        # Load configuration if provided
        if config_file and Path(config_file).exists():
            self.load_config(config_file)

    def load_config(self, config_file: str) -> None:
        """Load server configuration from file"""
        try:
            with open(config_file, "r") as f:
                config = json.load(f)

            for server_config in config.get("servers", []):
                server = ServerInstance(
                    name=server_config["name"],
                    host=server_config["host"],
                    port=server_config["port"],
                    mode=server_config.get("mode", "auto"),
                    weight=server_config.get("weight", 1),
                    health_check_url=server_config.get("health_check_url"),
                    metadata=server_config.get("metadata", {}),
                )
                self.servers[server.name] = server

            # Load coordination settings
            self.coordination_port = config.get("coordination_port", 2325)
            self.health_check_interval = config.get("health_check_interval", 10.0)
            self.load_balancer_enabled = config.get("load_balancer_enabled", True)
            self.failover_enabled = config.get("failover_enabled", True)

            logger.info(
                f"Loaded configuration for {len(self.servers)} servers from {config_file}"
            )

        except Exception as e:
            logger.error(f"Error loading config from {config_file}: {e}")

    def save_config(self, config_file: str) -> None:
        """Save current configuration to file"""
        config = {
            "servers": [
                {
                    "name": server.name,
                    "host": server.host,
                    "port": server.port,
                    "mode": server.mode,
                    "weight": server.weight,
                    "health_check_url": server.health_check_url,
                    "metadata": server.metadata,
                }
                for server in self.servers.values()
            ],
            "coordination_port": self.coordination_port,
            "health_check_interval": self.health_check_interval,
            "load_balancer_enabled": self.load_balancer_enabled,
            "failover_enabled": self.failover_enabled,
        }

        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)

        logger.info(f"Configuration saved to {config_file}")

    def add_server(self, server: ServerInstance) -> None:
        """Add a server instance to the coordination"""
        self.servers[server.name] = server
        logger.info(f"Added server {server.name} at {server.host}:{server.port}")

    def remove_server(self, server_name: str) -> None:
        """Remove a server from coordination"""
        if server_name in self.servers:
            del self.servers[server_name]
            logger.info(f"Removed server {server_name}")

    async def start_server(self, server_name: str) -> bool:
        """Start a specific server instance"""
        if server_name not in self.servers:
            logger.error(f"Server {server_name} not found")
            return False

        server = self.servers[server_name]
        if server.state in [ServerState.STARTING, ServerState.RUNNING]:
            logger.warning(f"Server {server_name} is already running")
            return True

        try:
            server.state = ServerState.STARTING
            logger.info(f"Starting server {server_name}...")

            # Start the enhanced test server
            cmd = [
                sys.executable,
                str(Path(__file__).parent / "enhanced_test_server.py"),
                "--host",
                server.host,
                "--port",
                str(server.port),
                "--mode",
                server.mode,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            server.process = process
            server.state = ServerState.RUNNING
            server.start_time = time.time()

            # Monitor the process
            task = asyncio.create_task(self._monitor_server_process(server))
            self.server_tasks[server_name] = task

            # Wait a moment for startup
            await asyncio.sleep(2)

            # Perform initial health check
            if await self._health_check_server(server):
                logger.info(f"Server {server_name} started successfully")
                return True
            else:
                logger.warning(f"Server {server_name} started but health check failed")
                return False

        except Exception as e:
            server.state = ServerState.FAILED
            logger.error(f"Failed to start server {server_name}: {e}")
            return False

    async def stop_server(self, server_name: str) -> bool:
        """Stop a specific server instance"""
        if server_name not in self.servers:
            logger.error(f"Server {server_name} not found")
            return False

        server = self.servers[server_name]
        server.state = ServerState.STOPPING

        try:
            # Cancel monitoring task
            if server_name in self.server_tasks:
                self.server_tasks[server_name].cancel()
                del self.server_tasks[server_name]

            # Terminate process
            if server.process:
                server.process.terminate()
                try:
                    await asyncio.wait_for(server.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning(f"Force killing server {server_name}")
                    server.process.kill()
                    await server.process.wait()

            server.state = ServerState.STOPPED
            server.process = None
            server.start_time = None

            logger.info(f"Server {server_name} stopped")
            return True

        except Exception as e:
            server.state = ServerState.FAILED
            logger.error(f"Error stopping server {server_name}: {e}")
            return False

    async def start_all_servers(self) -> Dict[str, bool]:
        """Start all configured servers"""
        results = {}
        for server_name in self.servers.keys():
            results[server_name] = await self.start_server(server_name)
        return results

    async def stop_all_servers(self) -> Dict[str, bool]:
        """Stop all running servers"""
        results = {}
        for server_name in list(self.servers.keys()):
            results[server_name] = await self.stop_server(server_name)
        return results

    async def _monitor_server_process(self, server: ServerInstance) -> None:
        """Monitor a server process for health and status"""
        try:
            while server.state == ServerState.RUNNING and server.process:
                # Check if process is still running
                returncode = server.process.returncode
                if returncode is not None:
                    logger.error(
                        f"Server {server.name} process exited with code {returncode}"
                    )
                    server.state = ServerState.FAILED
                    break

                # Perform health check
                healthy = await self._health_check_server(server)
                if not healthy:
                    server.error_count += 1
                    if server.error_count >= 3:  # 3 consecutive failures
                        logger.error(
                            f"Server {server.name} marked as failed after 3 health check failures"
                        )
                        server.state = ServerState.FAILED
                        break
                else:
                    server.error_count = 0

                await asyncio.sleep(self.health_check_interval)

        except asyncio.CancelledError:
            logger.info(f"Monitoring task cancelled for server {server.name}")
        except Exception as e:
            logger.error(f"Error monitoring server {server.name}: {e}")
            server.state = ServerState.FAILED

    async def _health_check_server(self, server: ServerInstance) -> bool:
        """Perform health check on a server"""
        try:
            # Try to connect to the server
            reader, writer = await asyncio.open_connection(server.host, server.port)
            writer.close()
            await writer.wait_closed()

            server.health_status = True
            server.last_health_check = time.time()
            return True

        except Exception as e:
            logger.debug(f"Health check failed for {server.name}: {e}")
            server.health_status = False
            server.last_health_check = time.time()
            return False

    async def start_health_monitoring(self) -> None:
        """Start continuous health monitoring"""
        self.running = True
        logger.info("Starting multi-server health monitoring")

        while self.running:
            try:
                # Check all servers
                for server in self.servers.values():
                    if server.state == ServerState.RUNNING:
                        await self._health_check_server(server)

                # Handle failover if enabled
                if self.failover_enabled:
                    await self._handle_failover()

                # Update load balancer if enabled
                if self.load_balancer_enabled:
                    await self._update_load_balancer()

                await asyncio.sleep(self.health_check_interval)

            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(self.health_check_interval)

    def stop_health_monitoring(self) -> None:
        """Stop health monitoring"""
        self.running = False
        logger.info("Stopped multi-server health monitoring")

    async def _handle_failover(self) -> None:
        """Handle server failover scenarios"""
        # Check for failed servers that should be restarted
        failed_servers = [
            s for s in self.servers.values() if s.state == ServerState.FAILED
        ]

        for server in failed_servers:
            if (
                server.error_count >= 3
            ):  # Only attempt failover for truly failed servers
                logger.info(f"Attempting failover for server {server.name}")

                # Simple failover: restart the server
                success = await self.start_server(server.name)
                if success:
                    logger.info(f"Failover successful for server {server.name}")
                else:
                    logger.error(f"Failover failed for server {server.name}")

    async def _update_load_balancer(self) -> None:
        """Update load balancer with current server status"""
        # Calculate connection distribution
        total_connections = sum(
            s.connection_count
            for s in self.servers.values()
            if s.state == ServerState.RUNNING
        )

        if total_connections == 0:
            return

        # Simple round-robin with weights
        for server in self.servers.values():
            if server.state == ServerState.RUNNING:
                expected_load = (
                    server.weight
                    / sum(
                        s.weight
                        for s in self.servers.values()
                        if s.state == ServerState.RUNNING
                    )
                ) * total_connections
                server.metadata["expected_load"] = int(expected_load)

    def get_server_status(self) -> Dict[str, Any]:
        """Get status of all servers"""
        status = {
            "coordinator": {
                "running": self.running,
                "coordination_port": self.coordination_port,
                "total_servers": len(self.servers),
                "running_servers": len(
                    [s for s in self.servers.values() if s.state == ServerState.RUNNING]
                ),
                "failed_servers": len(
                    [s for s in self.servers.values() if s.state == ServerState.FAILED]
                ),
            },
            "servers": {},
        }

        for name, server in self.servers.items():
            status["servers"][name] = {
                "state": server.state.value,
                "host": server.host,
                "port": server.port,
                "mode": server.mode,
                "weight": server.weight,
                "connection_count": server.connection_count,
                "error_count": server.error_count,
                "healthy": server.health_status,
                "uptime": time.time() - server.start_time if server.start_time else 0,
                "last_health_check": server.last_health_check,
            }

        return status

    def get_healthy_servers(self) -> List[ServerInstance]:
        """Get list of healthy (running and healthy) servers"""
        return [
            s
            for s in self.servers.values()
            if s.state == ServerState.RUNNING and s.health_status
        ]

    def get_server_by_load(self) -> List[ServerInstance]:
        """Get servers sorted by current load (connection count / weight)"""
        servers = [
            s
            for s in self.servers.values()
            if s.state == ServerState.RUNNING and s.health_status
        ]
        return sorted(servers, key=lambda s: s.connection_count / s.weight)

    async def distribute_connections(self, connection_count: int) -> List[str]:
        """Distribute connections across healthy servers"""
        healthy_servers = self.get_server_by_load()
        if not healthy_servers:
            return []

        servers_to_use = healthy_servers[: min(len(healthy_servers), connection_count)]
        server_names = [s.name for s in servers_to_use]

        logger.info(
            f"Distributing {connection_count} connections across servers: {server_names}"
        )
        return server_names

    async def run_distributed_test(
        self, test_duration: float, target_connections: int = 10
    ) -> Dict[str, Any]:
        """Run a distributed test across multiple servers"""
        logger.info(
            f"Starting distributed test: {target_connections} connections for {test_duration}s"
        )

        # Start all servers
        start_results = await self.start_all_servers()
        healthy_servers = [name for name, success in start_results.items() if success]

        if not healthy_servers:
            logger.error("No healthy servers available for distributed test")
            return {"error": "No healthy servers available"}

        # Distribute connections across servers
        server_distribution = await self.distribute_connections(target_connections)

        test_start_time = time.time()
        test_results = {
            "test_start": test_start_time,
            "duration": test_duration,
            "target_connections": target_connections,
            "servers_used": len(server_distribution),
            "server_distribution": {},
            "total_connections_attempted": 0,
            "total_connections_successful": 0,
            "errors": [],
        }

        # Start connection simulation tasks
        connection_tasks = []
        for i, server_name in enumerate(server_distribution):
            server = self.servers[server_name]
            # Calculate how many connections this server should handle
            server_connections = target_connections // len(server_distribution)
            if i < target_connections % len(server_distribution):
                server_connections += 1

            test_results["server_distribution"][server_name] = {
                "target_connections": server_connections,
                "successful_connections": 0,
                "failed_connections": 0,
            }

            # Create connection simulation tasks
            for conn_id in range(server_connections):
                task = asyncio.create_task(
                    self._simulate_connection(server, conn_id, test_duration)
                )
                connection_tasks.append((task, server_name))

        # Run all connection tasks
        results = await asyncio.gather(
            *[task for task, _ in connection_tasks], return_exceptions=True
        )

        # Collect results
        for i, (task, server_name) in enumerate(connection_tasks):
            result = results[i]
            test_results["total_connections_attempted"] += 1

            if isinstance(result, Exception):
                test_results["errors"].append(f"Connection {i} failed: {result}")
                test_results["server_distribution"][server_name][
                    "failed_connections"
                ] += 1
            else:
                test_results["total_connections_successful"] += 1
                test_results["server_distribution"][server_name][
                    "successful_connections"
                ] += 1

        test_results["test_end"] = time.time()
        test_results["actual_duration"] = (
            test_results["test_end"] - test_results["test_start"]
        )

        # Stop all servers
        await self.stop_all_servers()

        logger.info(
            f"Distributed test completed: {test_results['total_connections_successful']}/{test_results['total_connections_attempted']} successful"
        )
        return test_results

    async def _simulate_connection(
        self, server: ServerInstance, conn_id: int, duration: float
    ) -> None:
        """Simulate a client connection to a server"""
        try:
            start_time = time.time()

            # Connect to server
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(server.host, server.port), timeout=5.0
            )

            server.connection_count += 1

            # Stay connected for the test duration
            while time.time() - start_time < duration:
                try:
                    # Send some test data
                    test_data = f"test_{conn_id}_{int(time.time())}".encode()
                    writer.write(test_data)
                    await asyncio.wait_for(writer.drain(), timeout=1.0)

                    # Read response (with timeout)
                    await asyncio.wait_for(reader.read(1024), timeout=1.0)

                    await asyncio.sleep(random.uniform(0.1, 1.0))

                except asyncio.TimeoutError:
                    # Timeout is acceptable, just continue
                    await asyncio.sleep(0.1)
                except Exception as e:
                    # Other errors are also acceptable in this test
                    await asyncio.sleep(0.1)

            writer.close()
            await writer.wait_closed()
            server.connection_count -= 1

        except Exception as e:
            # Connection failures are expected in some test scenarios
            logger.debug(f"Connection {conn_id} to {server.name} failed: {e}")
            raise


# CLI interface for multi-server coordination
def main():
    """Multi-server coordinator CLI"""
    import argparse

    parser = argparse.ArgumentParser(description="Multi-Server TN3270 Test Coordinator")
    parser.add_argument("--config", help="Configuration file for server cluster")
    parser.add_argument(
        "--action",
        choices=["start", "stop", "status", "test"],
        default="status",
        help="Action to perform",
    )
    parser.add_argument(
        "--server", help="Specific server name for single-server actions"
    )
    parser.add_argument(
        "--test-duration",
        type=float,
        default=30.0,
        help="Duration for distributed test (seconds)",
    )
    parser.add_argument(
        "--target-connections",
        type=int,
        default=10,
        help="Number of connections for distributed test",
    )
    parser.add_argument(
        "--coordination-port",
        type=int,
        default=2325,
        help="Port for coordination service",
    )

    args = parser.parse_args()

    coordinator = MultiServerCoordinator(args.config)
    coordinator.coordination_port = args.coordination_port

    async def run_coordinator():
        if args.action == "start":
            if args.server:
                success = await coordinator.start_server(args.server)
                print(
                    f"Server {args.server} start: {'success' if success else 'failed'}"
                )
            else:
                results = await coordinator.start_all_servers()
                for name, success in results.items():
                    print(f"Server {name}: {'success' if success else 'failed'}")

        elif args.action == "stop":
            if args.server:
                success = await coordinator.stop_server(args.server)
                print(
                    f"Server {args.server} stop: {'success' if success else 'failed'}"
                )
            else:
                results = await coordinator.stop_all_servers()
                for name, success in results.items():
                    print(f"Server {name}: {'success' if success else 'failed'}")

        elif args.action == "status":
            status = coordinator.get_server_status()
            print(json.dumps(status, indent=2))

        elif args.action == "test":
            results = await coordinator.run_distributed_test(
                args.test_duration, args.target_connections
            )
            print(json.dumps(results, indent=2, default=str))

        # Start health monitoring if servers are running
        running_servers = [
            s for s in coordinator.servers.values() if s.state == ServerState.RUNNING
        ]
        if running_servers:
            logger.info("Starting health monitoring...")
            try:
                await coordinator.start_health_monitoring()
            except KeyboardInterrupt:
                coordinator.stop_health_monitoring()
                logger.info("Coordinator stopped by user")

    try:
        asyncio.run(run_coordinator())
    except KeyboardInterrupt:
        print("Coordinator stopped by user")
    except Exception as e:
        logger.error(f"Coordinator error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
