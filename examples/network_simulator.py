#!/usr/bin/env python3
"""
Network Simulator for Pure3270 Testing.

This module provides network simulation capabilities to test Pure3270's
robustness under various network conditions including:
- Latency/delay simulation
- Packet loss simulation
- Bandwidth throttling
- Connection interruptions
- Reordering of packets

Usage:
    python network_simulator.py --latency 100 --loss 0.01 --trace-file ibmlink.trc
"""

import argparse
import asyncio
import random
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional

# Add pure3270 to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class NetworkSimulator:
    """Simulates various network conditions for testing."""

    def __init__(
        self,
        latency_ms: float = 0,
        jitter_ms: float = 0,
        packet_loss: float = 0,
        bandwidth_kbps: Optional[float] = None,
        reorder_probability: float = 0,
        duplicate_probability: float = 0,
    ):
        self.latency_ms = latency_ms
        self.jitter_ms = jitter_ms
        self.packet_loss = packet_loss
        self.bandwidth_kbps = bandwidth_kbps
        self.reorder_probability = reorder_probability
        self.duplicate_probability = duplicate_probability

        # Internal state
        self.pending_packets = asyncio.PriorityQueue()
        self.sequence_counter = 0

    async def simulate_delay(self) -> float:
        """Calculate total delay for a packet."""
        base_delay = self.latency_ms / 1000.0  # Convert to seconds
        jitter = random.uniform(-self.jitter_ms, self.jitter_ms) / 1000.0
        return max(0, base_delay + jitter)

    def should_drop_packet(self) -> bool:
        """Determine if a packet should be dropped."""
        return random.random() < self.packet_loss

    def should_reorder_packet(self) -> bool:
        """Determine if a packet should be reordered."""
        return random.random() < self.reorder_probability

    def should_duplicate_packet(self) -> bool:
        """Determine if a packet should be duplicated."""
        return random.random() < self.duplicate_probability

    async def simulate_bandwidth_delay(self, packet_size_bytes: int) -> float:
        """Calculate delay based on bandwidth limitations."""
        if not self.bandwidth_kbps:
            return 0

        # Bandwidth in bits per second
        bandwidth_bps = self.bandwidth_kbps * 1000

        # Packet size in bits
        packet_size_bits = packet_size_bytes * 8

        # Transmission time in seconds
        transmission_time = packet_size_bits / bandwidth_bps

        return transmission_time

    async def send_with_simulation(
        self,
        data: bytes,
        send_func: Callable[[bytes], Any],
        direction: str = "outbound",
    ) -> None:
        """Send data through network simulation."""
        packet_size = len(data)
        self.sequence_counter += 1
        seq_num = self.sequence_counter

        # Check for packet loss
        if self.should_drop_packet():
            print(
                f"[NETSIM] [{direction}] Dropped packet {seq_num} ({packet_size} bytes)"
            )
            return

        # Calculate delays
        delay = await self.simulate_delay()
        bandwidth_delay = await self.simulate_bandwidth_delay(packet_size)
        total_delay = delay + bandwidth_delay

        # Check for duplication
        duplicate = self.should_duplicate_packet()

        # Check for reordering (add extra delay)
        reorder_delay = 0
        if self.should_reorder_packet():
            reorder_delay = random.uniform(0.01, 0.1)  # 10-100ms reordering delay
            total_delay += reorder_delay

        async def delayed_send():
            """Send packet after calculated delay."""
            await asyncio.sleep(total_delay)

            print(
                f"[NETSIM] [{direction}] Sending packet {seq_num} ({packet_size} bytes) "
                f"delay={total_delay:.3f}s"
            )

            await send_func(data)

            # Send duplicate if needed
            if duplicate:
                dup_delay = random.uniform(0.001, 0.01)  # 1-10ms duplicate delay
                await asyncio.sleep(dup_delay)
                print(f"[NETSIM] [{direction}] Sending duplicate packet {seq_num}")
                await send_func(data)

        # Schedule the delayed send
        asyncio.create_task(delayed_send())

    def get_stats(self) -> dict:
        """Get current network simulation statistics."""
        return {
            "latency_ms": self.latency_ms,
            "jitter_ms": self.jitter_ms,
            "packet_loss": self.packet_loss,
            "bandwidth_kbps": self.bandwidth_kbps,
            "reorder_probability": self.reorder_probability,
            "duplicate_probability": self.duplicate_probability,
        }


class SimulatedConnection:
    """A connection wrapper that applies network simulation."""

    def __init__(
        self,
        real_reader: asyncio.StreamReader,
        real_writer: asyncio.StreamWriter,
        network_sim: NetworkSimulator,
    ):
        self.real_reader = real_reader
        self.real_writer = real_writer
        self.network_sim = network_sim

    async def read(self, n: int = -1) -> bytes:
        """Read with network simulation."""
        data = await self.real_reader.read(n)

        if data:
            # Apply simulation to inbound data
            await self.network_sim.send_with_simulation(
                data, lambda d: self._simulate_receive(d), "inbound"
            )

        return data

    async def _simulate_receive(self, data: bytes) -> None:
        """Internal method for receive simulation."""
        # For inbound data, we just pass it through since the delay
        # was already applied in send_with_simulation
        pass

    def write(self, data: bytes) -> None:
        """Write with network simulation."""
        # Schedule the write with network simulation
        asyncio.create_task(
            self.network_sim.send_with_simulation(
                data, lambda d: self._do_write(d), "outbound"
            )
        )

    async def _do_write(self, data: bytes) -> None:
        """Actually perform the write."""
        self.real_writer.write(data)
        await self.real_writer.drain()

    def close(self) -> None:
        """Close the connection."""
        self.real_writer.close()

    async def wait_closed(self) -> None:
        """Wait for connection to close."""
        await self.real_writer.wait_closed()

    def get_extra_info(self, name: str, default=None):
        """Get connection info."""
        return self.real_writer.get_extra_info(name, default)


async def create_simulated_connection(
    host: str, port: int, network_sim: NetworkSimulator
) -> SimulatedConnection:
    """Create a connection with network simulation."""
    reader, writer = await asyncio.open_connection(host, port)
    return SimulatedConnection(reader, writer, network_sim)


def parse_network_args() -> argparse.ArgumentParser:
    """Create argument parser for network simulation options."""
    parser = argparse.ArgumentParser(
        description="Network Simulator for Pure3270 Testing"
    )

    parser.add_argument(
        "--latency", type=float, default=0, help="Base latency in milliseconds"
    )
    parser.add_argument(
        "--jitter", type=float, default=0, help="Jitter (±) in milliseconds"
    )
    parser.add_argument(
        "--loss", type=float, default=0, help="Packet loss probability (0.0-1.0)"
    )
    parser.add_argument("--bandwidth", type=float, help="Bandwidth limit in kbps")
    parser.add_argument(
        "--reorder",
        type=float,
        default=0,
        help="Packet reordering probability (0.0-1.0)",
    )
    parser.add_argument(
        "--duplicate",
        type=float,
        default=0,
        help="Packet duplication probability (0.0-1.0)",
    )

    return parser


def create_network_simulator_from_args(args) -> NetworkSimulator:
    """Create NetworkSimulator from parsed arguments."""
    return NetworkSimulator(
        latency_ms=args.latency,
        jitter_ms=args.jitter,
        packet_loss=args.loss,
        bandwidth_kbps=args.bandwidth,
        reorder_probability=args.reorder,
        duplicate_probability=args.duplicate,
    )


async def demo_network_simulation():
    """Demonstrate network simulation capabilities."""
    print("Network Simulator Demo")
    print("=" * 50)

    # Create simulator with various conditions
    sim = NetworkSimulator(
        latency_ms=50,  # 50ms base latency
        jitter_ms=10,  # ±10ms jitter
        packet_loss=0.05,  # 5% packet loss
        bandwidth_kbps=100,  # 100 kbps limit
        reorder_probability=0.1,  # 10% reordering
        duplicate_probability=0.02,  # 2% duplication
    )

    print("Network conditions:")
    stats = sim.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\nSimulating packet transmission...")

    # Simulate sending some packets
    async def mock_send(data: bytes):
        print(f"  -> Sent {len(data)} bytes: {data.hex()[:20]}...")

    packets = [
        b"Hello World",
        b"This is a test packet",
        b"TN3270 data stream example",
        b"More data to send",
        b"Final packet",
    ]

    tasks = []
    for packet in packets:
        task = sim.send_with_simulation(packet, mock_send, "demo")
        tasks.append(task)

    await asyncio.gather(*tasks)

    # Wait for all delayed sends to complete
    await asyncio.sleep(1)

    print("\nDemo complete!")


if __name__ == "__main__":
    # If run directly, show demo
    asyncio.run(demo_network_simulation())
