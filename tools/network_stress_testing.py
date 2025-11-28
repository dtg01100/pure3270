#!/usr/bin/env python3
"""
Network Interruption and Resource Stress Testing

Provides comprehensive network interruption simulation and system resource
stress testing capabilities for TN3270 testing scenarios.

Features:
- Network interruption simulation (drops, delays, corruption)
- Connection lifecycle testing
- Timeout and retry scenario simulation
- Memory pressure and resource exhaustion testing
- CPU stress testing
- Network bandwidth limitation
- Server resilience testing
- Recovery scenario testing
"""

import asyncio
import gc
import json
import logging
import os
import random
import resource
import signal
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil

# Add pure3270 to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class InterruptionType(Enum):
    """Types of network interruptions"""

    CONNECTION_DROP = "connection_drop"
    DATA_LOSS = "data_loss"
    DELAY_INJECTION = "delay_injection"
    BANDWIDTH_THROTTLING = "bandwidth_throttling"
    PACKET_CORRUPTION = "packet_corruption"
    TIMEOUT_SIMULATION = "timeout_simulation"
    NETWORK_PARTITION = "network_partition"
    BURST_INTERRUPTION = "burst_interruption"


class StressType(Enum):
    """Types of stress testing"""

    MEMORY_PRESSURE = "memory_pressure"
    CPU_STRAIN = "cpu_strain"
    CONNECTION_FLOOD = "connection_flood"
    BANDWIDTH_EXHAUSTION = "bandwidth_exhaustion"
    FILE_DESCRIPTOR_EXHAUSTION = "fd_exhaustion"
    THREAD_EXHAUSTION = "thread_exhaustion"


@dataclass
class InterruptionScenario:
    """Network interruption scenario configuration"""

    name: str
    interruption_type: InterruptionType
    probability: float  # 0.0 to 1.0
    duration: float  # seconds
    interval: float  # seconds between interruptions
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    description: str = ""


@dataclass
class StressTestConfig:
    """Stress test configuration"""

    name: str
    stress_type: StressType
    intensity: float  # 0.0 to 1.0
    duration: float
    target_resources: List[str] = field(default_factory=list)
    monitoring_enabled: bool = True
    recovery_test: bool = True


class NetworkInterruptionSimulator:
    """Simulates various network interruption scenarios"""

    def __init__(self):
        self.scenarios: List[InterruptionScenario] = []
        self.active_interruptions: Dict[str, asyncio.Task] = {}
        self.interruption_stats = {
            "total_triggered": 0,
            "successful": 0,
            "failed": 0,
            "by_type": {},
        }

    def add_scenario(self, scenario: InterruptionScenario) -> None:
        """Add an interruption scenario"""
        self.scenarios.append(scenario)
        logger.info(
            f"Added interruption scenario: {scenario.name} ({scenario.interruption_type.value})"
        )

    def start_scenario(
        self, scenario: InterruptionScenario, connection_id: str
    ) -> bool:
        """Start an interruption scenario for a specific connection"""
        if not scenario.enabled or scenario not in self.scenarios:
            return False

        if connection_id in self.active_interruptions:
            return False

        # Create interruption task
        task = asyncio.create_task(
            self._run_interruption_scenario(scenario, connection_id)
        )
        self.active_interruptions[connection_id] = task

        # Update stats
        self.interruption_stats["total_triggered"] += 1
        interruption_type = scenario.interruption_type.value
        if interruption_type not in self.interruption_stats["by_type"]:
            self.interruption_stats["by_type"][interruption_type] = 0
        self.interruption_stats["by_type"][interruption_type] += 1

        return True

    def stop_scenario(self, connection_id: str) -> bool:
        """Stop an interruption scenario for a connection"""
        if connection_id in self.active_interruptions:
            self.active_interruptions[connection_id].cancel()
            del self.active_interruptions[connection_id]
            return True
        return False

    async def _run_interruption_scenario(
        self, scenario: InterruptionScenario, connection_id: str
    ) -> None:
        """Run an interruption scenario"""
        try:
            start_time = time.time()

            while (time.time() - start_time) < scenario.duration:
                # Check if interruption should be triggered
                if random.random() < scenario.probability:
                    success = await self._trigger_interruption(scenario, connection_id)
                    if success:
                        self.interruption_stats["successful"] += 1
                    else:
                        self.interruption_stats["failed"] += 1

                # Wait for next interval
                await asyncio.sleep(scenario.interval)

        except asyncio.CancelledError:
            logger.info(
                f"Interruption scenario {scenario.name} cancelled for {connection_id}"
            )
        except Exception as e:
            logger.error(f"Error in interruption scenario {scenario.name}: {e}")
            self.interruption_stats["failed"] += 1

    async def _trigger_interruption(
        self, scenario: InterruptionScenario, connection_id: str
    ) -> bool:
        """Trigger the actual interruption"""
        try:
            if scenario.interruption_type == InterruptionType.CONNECTION_DROP:
                return await self._simulate_connection_drop(connection_id)
            elif scenario.interruption_type == InterruptionType.DATA_LOSS:
                return await self._simulate_data_loss(
                    connection_id, scenario.parameters
                )
            elif scenario.interruption_type == InterruptionType.DELAY_INJECTION:
                return await self._simulate_delay_injection(
                    connection_id, scenario.parameters
                )
            elif scenario.interruption_type == InterruptionType.BANDWIDTH_THROTTLING:
                return await self._simulate_bandwidth_throttling(
                    connection_id, scenario.parameters
                )
            elif scenario.interruption_type == InterruptionType.PACKET_CORRUPTION:
                return await self._simulate_packet_corruption(
                    connection_id, scenario.parameters
                )
            elif scenario.interruption_type == InterruptionType.TIMEOUT_SIMULATION:
                return await self._simulate_timeout(connection_id, scenario.parameters)
            elif scenario.interruption_type == InterruptionType.NETWORK_PARTITION:
                return await self._simulate_network_partition(
                    connection_id, scenario.parameters
                )
            elif scenario.interruption_type == InterruptionType.BURST_INTERRUPTION:
                return await self._simulate_burst_interruption(
                    connection_id, scenario.parameters
                )

            return False
        except Exception as e:
            logger.error(
                f"Error triggering interruption {scenario.interruption_type.value}: {e}"
            )
            return False

    async def _simulate_connection_drop(self, connection_id: str) -> bool:
        """Simulate connection drop"""
        logger.warning(f"Simulating connection drop for {connection_id}")
        # In a real implementation, this would close the actual connection
        await asyncio.sleep(0.1)  # Simulate drop delay
        return True

    async def _simulate_data_loss(
        self, connection_id: str, parameters: Dict[str, Any]
    ) -> bool:
        """Simulate data loss during transmission"""
        loss_rate = parameters.get("loss_rate", 0.1)
        duration = parameters.get("duration", 1.0)

        logger.info(f"Simulating data loss ({loss_rate*100:.1f}%) for {connection_id}")

        # Simulate data loss period
        await asyncio.sleep(duration)
        return True

    async def _simulate_delay_injection(
        self, connection_id: str, parameters: Dict[str, Any]
    ) -> bool:
        """Simulate network delay injection"""
        delay_ms = parameters.get("delay_ms", 100)
        logger.info(f"Simulating network delay ({delay_ms}ms) for {connection_id}")

        await asyncio.sleep(delay_ms / 1000.0)
        return True

    async def _simulate_bandwidth_throttling(
        self, connection_id: str, parameters: Dict[str, Any]
    ) -> bool:
        """Simulate bandwidth throttling"""
        bandwidth_kbps = parameters.get("bandwidth_kbps", 64)
        logger.info(
            f"Simulating bandwidth throttling ({bandwidth_kbps}Kbps) for {connection_id}"
        )

        # Simulate bandwidth-limited period
        await asyncio.sleep(2.0)  # Duration of throttling
        return True

    async def _simulate_packet_corruption(
        self, connection_id: str, parameters: Dict[str, Any]
    ) -> bool:
        """Simulate packet corruption"""
        corruption_rate = parameters.get("corruption_rate", 0.05)
        logger.info(
            f"Simulating packet corruption ({corruption_rate*100:.1f}%) for {connection_id}"
        )

        await asyncio.sleep(1.0)  # Duration of corruption
        return True

    async def _simulate_timeout(
        self, connection_id: str, parameters: Dict[str, Any]
    ) -> bool:
        """Simulate connection timeout"""
        timeout_seconds = parameters.get("timeout_seconds", 30)
        logger.info(f"Simulating timeout ({timeout_seconds}s) for {connection_id}")

        await asyncio.sleep(min(timeout_seconds, 5.0))  # Cap for testing
        return True

    async def _simulate_network_partition(
        self, connection_id: str, parameters: Dict[str, Any]
    ) -> bool:
        """Simulate network partition"""
        partition_duration = parameters.get("duration", 10.0)
        logger.warning(
            f"Simulating network partition ({partition_duration}s) for {connection_id}"
        )

        await asyncio.sleep(min(partition_duration, 5.0))  # Cap for testing
        return True

    async def _simulate_burst_interruption(
        self, connection_id: str, parameters: Dict[str, Any]
    ) -> bool:
        """Simulate burst of interruptions"""
        burst_count = parameters.get("burst_count", 5)
        burst_interval = parameters.get("burst_interval", 0.5)

        logger.info(
            f"Simulating burst interruption ({burst_count} events) for {connection_id}"
        )

        for i in range(burst_count):
            if i > 0:
                await asyncio.sleep(burst_interval)

            # Simulate random interruption
            interruption_types = list(InterruptionType)
            selected_type = random.choice(interruption_types)
            logger.debug(
                f"Burst event {i+1}: {selected_type.value} for {connection_id}"
            )

        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get interruption statistics"""
        return {
            "active_interruptions": len(self.active_interruptions),
            "total_scenarios": len(self.scenarios),
            "statistics": self.interruption_stats.copy(),
        }


class ResourceStressTester:
    """Resource stress testing for system resilience"""

    def __init__(self):
        self.active_tests: Dict[str, StressTestConfig] = {}
        self.stress_tasks: Dict[str, asyncio.Task] = {}
        self.monitoring_data: List[Dict[str, Any]] = []
        self.base_metrics = {}
        self.stress_stats = {
            "tests_started": 0,
            "tests_completed": 0,
            "tests_failed": 0,
            "resource_exhaustion_events": 0,
            "recovery_successes": 0,
            "recovery_failures": 0,
        }

    def add_test_config(self, config: StressTestConfig) -> None:
        """Add a stress test configuration"""
        self.active_tests[config.name] = config
        logger.info(f"Added stress test: {config.name} ({config.stress_type.value})")

    def start_stress_test(self, test_name: str) -> bool:
        """Start a stress test"""
        if test_name not in self.active_tests:
            logger.error(f"Stress test not found: {test_name}")
            return False

        if test_name in self.stress_tasks:
            logger.warning(f"Stress test already running: {test_name}")
            return True

        config = self.active_tests[test_name]

        # Capture baseline metrics
        self.base_metrics = self._capture_system_metrics()

        # Start monitoring if enabled
        if config.monitoring_enabled:
            monitor_task = asyncio.create_task(self._monitor_resources(config.duration))

        # Start stress test
        task = asyncio.create_task(self._run_stress_test(config))
        self.stress_tasks[test_name] = task

        self.stress_stats["tests_started"] += 1
        logger.info(f"Started stress test: {test_name}")

        return True

    async def _run_stress_test(self, config: StressTestConfig) -> None:
        """Run the actual stress test"""
        try:
            start_time = time.time()

            # Run the appropriate stress test
            if config.stress_type == StressType.MEMORY_PRESSURE:
                await self._run_memory_pressure_test(config)
            elif config.stress_type == StressType.CPU_STRAIN:
                await self._run_cpu_strain_test(config)
            elif config.stress_type == StressType.CONNECTION_FLOOD:
                await self._run_connection_flood_test(config)
            elif config.stress_type == StressType.BANDWIDTH_EXHAUSTION:
                await self._run_bandwidth_exhaustion_test(config)
            elif config.stress_type == StressType.FILE_DESCRIPTOR_EXHAUSTION:
                await self._run_fd_exhaustion_test(config)
            elif config.stress_type == StressType.THREAD_EXHAUSTION:
                await self._run_thread_exhaustion_test(config)

            # Test recovery if enabled
            if config.recovery_test:
                await self._test_recovery(config)

            self.stress_stats["tests_completed"] += 1
            logger.info(f"Completed stress test: {config.name}")

        except Exception as e:
            logger.error(f"Stress test {config.name} failed: {e}")
            self.stress_stats["tests_failed"] += 1

    async def _run_memory_pressure_test(self, config: StressTestConfig) -> None:
        """Run memory pressure test"""
        intensity = config.intensity
        target_memory_mb = int(100 * intensity)  # 0-100MB depending on intensity

        logger.info(f"Running memory pressure test: {target_memory_mb}MB")

        allocated_blocks = []
        block_size = 1024 * 1024  # 1MB blocks

        try:
            while len(allocated_blocks) < target_memory_mb:
                # Allocate memory blocks
                block = bytearray(block_size)
                # Fill with data to ensure actual allocation
                block[:] = b"A" * block_size
                allocated_blocks.append(block)

                # Check memory usage
                current_metrics = self._capture_system_metrics()
                if current_metrics["memory_percent"] > 90:
                    logger.warning("High memory usage detected")
                    self.stress_stats["resource_exhaustion_events"] += 1

                await asyncio.sleep(0.1)

            # Hold memory for a bit
            await asyncio.sleep(config.duration / 2)

        finally:
            # Clean up allocated memory
            allocated_blocks.clear()
            gc.collect()

    async def _run_cpu_strain_test(self, config: StressTestConfig) -> None:
        """Run CPU strain test"""
        intensity = config.intensity
        cpu_target = int(50 + (50 * intensity))  # 50-100% CPU usage

        logger.info(f"Running CPU strain test: {cpu_target}% target")

        # Number of worker tasks based on intensity
        num_workers = int(2 + (8 * intensity))  # 2-10 workers

        async def cpu_worker():
            """CPU-intensive work"""
            end_time = time.time() + config.duration
            while time.time() < end_time:
                # Perform CPU-intensive calculations
                for i in range(1000):
                    _ = sum(range(100))
                await asyncio.sleep(0.001)  # Small yield

        # Start worker tasks
        workers = [asyncio.create_task(cpu_worker()) for _ in range(num_workers)]

        try:
            # Monitor CPU usage
            while time.time() < (time.time() + config.duration):
                metrics = self._capture_system_metrics()
                if metrics["cpu_percent"] > 90:
                    logger.warning("High CPU usage detected")
                    self.stress_stats["resource_exhaustion_events"] += 1
                await asyncio.sleep(0.5)

            # Wait for workers to complete
            await asyncio.gather(*workers)

        except Exception as e:
            # Cancel workers on error
            for worker in workers:
                worker.cancel()
            raise

    async def _run_connection_flood_test(self, config: StressTestConfig) -> None:
        """Run connection flood test"""
        intensity = config.intensity
        target_connections = int(10 + (100 * intensity))  # 10-110 connections

        logger.info(f"Running connection flood test: {target_connections} connections")

        connection_tasks = []

        for i in range(target_connections):
            task = asyncio.create_task(self._simulate_connection(i))
            connection_tasks.append(task)
            await asyncio.sleep(0.01)  # Small delay between connection attempts

        # Wait for some connections to complete
        await asyncio.sleep(config.duration)

        # Clean up remaining tasks
        for task in connection_tasks:
            if not task.done():
                task.cancel()

    async def _simulate_connection(self, conn_id: int) -> None:
        """Simulate a connection for flood testing"""
        try:
            # Simulate connection establishment
            await asyncio.sleep(random.uniform(0.1, 1.0))

            # Keep connection alive for a bit
            await asyncio.sleep(random.uniform(0.5, 3.0))

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Connection {conn_id} failed: {e}")

    async def _run_bandwidth_exhaustion_test(self, config: StressTestConfig) -> None:
        """Run bandwidth exhaustion test"""
        intensity = config.intensity
        target_bandwidth_mbps = int(10 + (90 * intensity))  # 10-100 Mbps

        logger.info(f"Running bandwidth exhaustion test: {target_bandwidth_mbps}Mbps")

        # Simulate high bandwidth usage
        data_size = 1024 * 1024  # 1MB chunks
        end_time = time.time() + config.duration

        while time.time() < end_time:
            # Simulate sending large amounts of data
            data = b"X" * data_size
            await asyncio.sleep(0.1)  # Brief pause between chunks

            # Check network usage
            metrics = self._capture_system_metrics()
            if hasattr(metrics, "network") and metrics["network"]:
                network = metrics["network"]
                if network.get("bytes_sent", 0) > 0:
                    logger.debug(f"Network usage: {network}")

    async def _run_fd_exhaustion_test(self, config: StressTestConfig) -> None:
        """Run file descriptor exhaustion test"""
        intensity = config.intensity
        target_fds = int(50 + (400 * intensity))  # 50-450 FDs

        logger.info(f"Running FD exhaustion test: {target_fds} file descriptors")

        # Open many file descriptors
        open_files = []

        try:
            for i in range(target_fds):
                # Open dummy files
                try:
                    # Create temp file in the system temp dir instead of hardcoded /tmp
                    fd, file_path = tempfile.mkstemp(prefix=f"fd_test_{i}_")
                    # mkstemp returns an open fd and path
                    # nosec B108: using system tempdir via tempfile avoids hardcoded /tmp
                    open_files.append((fd, file_path))
                except OSError:
                    logger.warning(f"Failed to open FD {i}")
                    self.stress_stats["resource_exhaustion_events"] += 1
                    break

                await asyncio.sleep(0.01)

            # Hold FDs open for a bit
            await asyncio.sleep(config.duration / 2)

        finally:
            # Clean up file descriptors
            for fd, file_path in open_files:
                try:
                    os.close(fd)
                    os.unlink(file_path)
                except:
                    pass

    async def _run_thread_exhaustion_test(self, config: StressTestConfig) -> None:
        """Run thread exhaustion test"""
        intensity = config.intensity
        target_threads = int(10 + (90 * intensity))  # 10-100 threads

        logger.info(f"Running thread exhaustion test: {target_threads} threads")

        active_threads = []

        async def thread_worker(thread_id: int):
            """Worker function for thread stress"""
            try:
                await asyncio.sleep(config.duration)
            except asyncio.CancelledError:
                pass

        try:
            # Start many threads
            for i in range(target_threads):
                task = asyncio.create_task(thread_worker(i))
                active_threads.append(task)
                await asyncio.sleep(0.01)

            # Wait for some time
            await asyncio.sleep(config.duration / 2)

        finally:
            # Clean up threads
            for task in active_threads:
                task.cancel()

            # Wait for cancellation
            await asyncio.gather(*active_threads, return_exceptions=True)

    async def _test_recovery(self, config: StressTestConfig) -> None:
        """Test system recovery after stress"""
        logger.info(f"Testing recovery for {config.name}")

        # Simulate recovery period
        await asyncio.sleep(2.0)

        # Check if system has recovered
        current_metrics = self._capture_system_metrics()
        recovery_threshold = 0.8  # 80% of baseline is considered recovered

        if self._check_recovery(current_metrics, self.base_metrics, recovery_threshold):
            self.stress_stats["recovery_successes"] += 1
            logger.info(f"Recovery successful for {config.name}")
        else:
            self.stress_stats["recovery_failures"] += 1
            logger.warning(f"Recovery failed for {config.name}")

    def _check_recovery(
        self, current: Dict[str, Any], baseline: Dict[str, Any], threshold: float
    ) -> bool:
        """Check if system has recovered to acceptable levels"""
        if not current or not baseline:
            return False

        # Check memory recovery
        current_mem = current.get("memory_percent", 100)
        baseline_mem = baseline.get("memory_percent", 50)

        if current_mem > (baseline_mem * (1 + threshold)):
            return False

        # Check CPU recovery
        current_cpu = current.get("cpu_percent", 100)
        baseline_cpu = baseline.get("cpu_percent", 20)

        if current_cpu > (baseline_cpu * (1 + threshold)):
            return False

        return True

    def _capture_system_metrics(self) -> Dict[str, Any]:
        """Capture current system metrics"""
        try:
            return {
                "timestamp": time.time(),
                "cpu_percent": psutil.cpu_percent(interval=None),
                "memory_percent": psutil.virtual_memory().percent,
                "memory_used_mb": psutil.virtual_memory().used / (1024 * 1024),
                "memory_available_mb": psutil.virtual_memory().available
                / (1024 * 1024),
                "disk_usage_percent": psutil.disk_usage("/").percent,
                "open_files": len(psutil.Process().open_files()),
                "threads": psutil.Process().num_threads(),
                "connections": len(psutil.net_connections()),
            }
        except Exception as e:
            logger.error(f"Error capturing metrics: {e}")
            return {}

    async def _monitor_resources(self, duration: float) -> None:
        """Monitor resource usage during stress test"""
        end_time = time.time() + duration

        while time.time() < end_time:
            metrics = self._capture_system_metrics()
            if metrics:
                self.monitoring_data.append(metrics)
            await asyncio.sleep(1.0)

    def get_stress_stats(self) -> Dict[str, Any]:
        """Get stress testing statistics"""
        return {
            "active_tests": len(self.stress_tasks),
            "configured_tests": len(self.active_tests),
            "statistics": self.stress_stats.copy(),
            "current_metrics": self._capture_system_metrics(),
            "monitoring_samples": len(self.monitoring_data),
        }


# Predefined test scenarios
def create_interruption_test_scenarios() -> List[InterruptionScenario]:
    """Create network interruption test scenarios"""
    return [
        InterruptionScenario(
            name="occasional_drops",
            interruption_type=InterruptionType.CONNECTION_DROP,
            probability=0.1,
            duration=30.0,
            interval=10.0,
            description="Occasional connection drops (10% chance every 10s)",
        ),
        InterruptionScenario(
            name="data_loss",
            interruption_type=InterruptionType.DATA_LOSS,
            probability=0.05,
            duration=60.0,
            interval=15.0,
            parameters={"loss_rate": 0.2, "duration": 2.0},
            description="Intermittent data loss (5% chance)",
        ),
        InterruptionScenario(
            name="network_delays",
            interruption_type=InterruptionType.DELAY_INJECTION,
            probability=0.3,
            duration=45.0,
            interval=5.0,
            parameters={"delay_ms": 500},
            description="Random network delays (30% chance, 500ms delay)",
        ),
        InterruptionScenario(
            name="bandwidth_throttling",
            interruption_type=InterruptionType.BANDWIDTH_THROTTLING,
            probability=0.15,
            duration=40.0,
            interval=20.0,
            parameters={"bandwidth_kbps": 64},
            description="Bandwidth throttling (15% chance, 64Kbps)",
        ),
        InterruptionScenario(
            name="packet_corruption",
            interruption_type=InterruptionType.PACKET_CORRUPTION,
            probability=0.08,
            duration=50.0,
            interval=12.0,
            parameters={"corruption_rate": 0.1},
            description="Packet corruption (8% chance, 10% corruption rate)",
        ),
        InterruptionScenario(
            name="timeout_simulation",
            interruption_type=InterruptionType.TIMEOUT_SIMULATION,
            probability=0.05,
            duration=60.0,
            interval=30.0,
            parameters={"timeout_seconds": 30},
            description="Connection timeout simulation (5% chance, 30s timeout)",
        ),
        InterruptionScenario(
            name="burst_interruptions",
            interruption_type=InterruptionType.BURST_INTERRUPTION,
            probability=0.02,
            duration=120.0,
            interval=60.0,
            parameters={"burst_count": 5, "burst_interval": 0.5},
            description="Burst of interruptions (2% chance, 5 events)",
        ),
    ]


def create_stress_test_configs() -> List[StressTestConfig]:
    """Create resource stress test configurations"""
    return [
        StressTestConfig(
            name="memory_pressure_mild",
            stress_type=StressType.MEMORY_PRESSURE,
            intensity=0.3,
            duration=30.0,
            target_resources=["memory"],
            monitoring_enabled=True,
            recovery_test=True,
        ),
        StressTestConfig(
            name="memory_pressure_severe",
            stress_type=StressType.MEMORY_PRESSURE,
            intensity=0.8,
            duration=60.0,
            target_resources=["memory"],
            monitoring_enabled=True,
            recovery_test=True,
        ),
        StressTestConfig(
            name="cpu_strain_moderate",
            stress_type=StressType.CPU_STRAIN,
            intensity=0.5,
            duration=45.0,
            target_resources=["cpu"],
            monitoring_enabled=True,
            recovery_test=True,
        ),
        StressTestConfig(
            name="cpu_strain_heavy",
            stress_type=StressType.CPU_STRAIN,
            intensity=0.9,
            duration=30.0,
            target_resources=["cpu"],
            monitoring_enabled=True,
            recovery_test=True,
        ),
        StressTestConfig(
            name="connection_flood",
            stress_type=StressType.CONNECTION_FLOOD,
            intensity=0.7,
            duration=40.0,
            target_resources=["connections"],
            monitoring_enabled=True,
            recovery_test=True,
        ),
        StressTestConfig(
            name="bandwidth_exhaustion",
            stress_type=StressType.BANDWIDTH_EXHAUSTION,
            intensity=0.6,
            duration=35.0,
            target_resources=["network"],
            monitoring_enabled=True,
            recovery_test=True,
        ),
    ]


# CLI interface
def main():
    """Network interruption and stress testing CLI"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Network Interruption and Stress Testing"
    )
    parser.add_argument(
        "--action",
        choices=["list", "interrupt", "stress", "both"],
        default="list",
        help="Action to perform",
    )
    parser.add_argument("--scenario", help="Specific scenario to run")
    parser.add_argument(
        "--duration", type=float, default=30.0, help="Test duration in seconds"
    )
    parser.add_argument(
        "--intensity", type=float, default=0.5, help="Test intensity (0.0-1.0)"
    )
    parser.add_argument("--output-file", help="Output file for test results")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    async def run_tests():
        results = {}

        if args.action in ["interrupt", "both"]:
            # Test network interruptions
            interrupt_sim = NetworkInterruptionSimulator()

            for scenario in create_interruption_test_scenarios():
                interrupt_sim.add_scenario(scenario)

            if args.scenario and args.scenario in [
                s.name for s in create_interruption_test_scenarios()
            ]:
                scenario = next(
                    s
                    for s in create_interruption_test_scenarios()
                    if s.name == args.scenario
                )
                logger.info(f"Running interruption scenario: {scenario.name}")

                # Simulate running the scenario
                await asyncio.sleep(min(args.duration, 5.0))  # Cap for testing

                results["interruption_test"] = {
                    "scenario": scenario.name,
                    "duration": args.duration,
                    "statistics": interrupt_sim.get_stats(),
                }
            else:
                results["interruption_available_scenarios"] = [
                    s.name for s in create_interruption_test_scenarios()
                ]

        if args.action in ["stress", "both"]:
            # Test resource stress
            stress_tester = ResourceStressTester()

            for config in create_stress_test_configs():
                stress_tester.add_test_config(config)

            if args.scenario and args.scenario in create_stress_test_configs():
                config = next(
                    c for c in create_stress_test_configs() if c.name == args.scenario
                )
                logger.info(f"Running stress test: {config.name}")

                # Simulate running the test (with capped duration)
                await asyncio.sleep(min(args.duration, 3.0))  # Cap for testing

                results["stress_test"] = {
                    "config": config.name,
                    "duration": args.duration,
                    "intensity": args.intensity,
                    "statistics": stress_tester.get_stress_stats(),
                }
            else:
                results["stress_available_tests"] = [
                    c.name for c in create_stress_test_configs()
                ]

        # Save results
        if args.output_file:
            with open(args.output_file, "w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Test results saved to {args.output_file}")
        else:
            print(json.dumps(results, indent=2, default=str))

    try:
        asyncio.run(run_tests())
    except KeyboardInterrupt:
        print("Testing interrupted by user")
    except Exception as e:
        logger.error(f"Test error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
