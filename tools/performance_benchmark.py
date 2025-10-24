#!/usr/bin/env python3
"""
Performance benchmarking tool for Pure3270.

This tool measures the performance of Pure3270 components with synthetic workloads.
"""

import os
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Add pure3270 to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pure3270.emulation.addressing import AddressCalculator, AddressingMode
from pure3270.emulation.screen_buffer import ScreenBuffer


def benchmark_screen_buffer_operations(iterations: int = 1000) -> Dict[str, Any]:
    """Benchmark screen buffer operations."""
    print(f"Benchmarking screen buffer operations ({iterations} iterations)...")

    # Create a screen buffer
    buffer = ScreenBuffer(24, 80)

    # Test data - EBCDIC bytes
    test_bytes = [
        0xC8,
        0x85,
        0x93,
        0x93,
        0x96,
        0x40,
        0xE6,
        0x96,
        0x99,
        0x93,
        0x84,
    ]  # "Hello World"

    # Benchmark write operations
    start_time = time.time()
    for i in range(iterations):
        row = i % 24
        col = i % 80
        ebcdic_byte = test_bytes[i % len(test_bytes)]
        buffer.write_char(ebcdic_byte, row, col)
    write_time = time.time() - start_time

    # Benchmark read operations (get content)
    start_time = time.time()
    for i in range(min(100, iterations)):  # Read fewer for speed
        _ = buffer.get_content()
    read_time = time.time() - start_time

    return {
        "operation": "screen_buffer",
        "iterations": iterations,
        "write_time": write_time,
        "read_time": read_time,
        "write_ops_per_sec": iterations / write_time,
        "read_ops_per_sec": min(100, iterations) / read_time,
    }


def benchmark_data_stream_parsing(streams: int = 100) -> Dict[str, Any]:
    """Benchmark TN3270 data stream parsing using synthetic data generator."""
    print(f"Benchmarking data stream parsing ({streams} streams)...")

    # Use the synthetic data generator's test function which already parses streams
    start_time = time.time()
    result = subprocess.run(
        [
            sys.executable,
            "tools/synthetic_data_generator.py",
            "generate",
            "benchmark_data",
            str(streams),
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    generation_time = time.time() - start_time

    if result.returncode != 0:
        print(f"Failed to generate synthetic data: {result.stderr}")
        return {"operation": "data_parsing", "error": "generation_failed"}

    # Test parsing the generated data
    start_time = time.time()
    result = subprocess.run(
        [
            sys.executable,
            "tools/synthetic_data_generator.py",
            "test",
            "benchmark_data/synthetic_test_cases.json",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    parsing_time = time.time() - start_time

    # Clean up
    import shutil

    shutil.rmtree("benchmark_data", ignore_errors=True)

    if result.returncode == 0:
        # Parse the output to get stats
        output_lines = result.stdout.strip().split("\n")
        success_line = [
            line for line in output_lines if "streams parsed successfully" in line
        ]
        if success_line:
            # Format: "Test Results: 2/2 streams parsed successfully"
            line = success_line[0]
            ratio_part = line.split(":")[1].split()[0]  # "2/2"
            successful, total = map(int, ratio_part.split("/"))
            return {
                "operation": "data_parsing",
                "streams": streams,
                "successful": successful,
                "total": total,
                "generation_time": generation_time,
                "parsing_time": parsing_time,
                "total_time": generation_time + parsing_time,
                "streams_per_sec": streams / (generation_time + parsing_time),
            }
        else:
            return {"operation": "data_parsing", "error": "no_success_line"}
    else:
        return {"operation": "data_parsing", "error": "parsing_failed"}


def benchmark_addressing_operations(iterations: int = 10000) -> Dict[str, Any]:
    """Benchmark addressing operations."""
    print(f"Benchmarking addressing operations ({iterations} iterations)...")

    # Benchmark address calculations using AddressCalculator
    addresses = []
    start_time = time.time()
    for i in range(iterations):
        row = i % 24
        col = i % 80
        addr = AddressCalculator.coords_to_address(
            row, col, 80, AddressingMode.MODE_12_BIT
        )
        addresses.append(addr)
    creation_time = time.time() - start_time

    # Benchmark address conversions
    start_time = time.time()
    for addr in addresses:
        coords = AddressCalculator.address_to_coords(
            addr, 80, AddressingMode.MODE_12_BIT
        )
        if coords is not None:
            row, col = coords
            _ = row, col
    calc_time = time.time() - start_time

    return {
        "operation": "addressing",
        "iterations": iterations,
        "creation_time": creation_time,
        "calc_time": calc_time,
        "creation_ops_per_sec": iterations / creation_time,
        "calc_ops_per_sec": iterations / calc_time,
    }


def run_benchmarks() -> List[Dict[str, Any]]:
    """Run all benchmarks."""
    print("🚀 Pure3270 Performance Benchmark Suite")
    print("=" * 50)

    results = []

    # Screen buffer operations
    results.append(benchmark_screen_buffer_operations())

    # Data stream parsing
    results.append(benchmark_data_stream_parsing())

    # Addressing operations
    results.append(benchmark_addressing_operations())

    return results


def print_results(results: List[Dict[str, Any]]):
    """Print benchmark results."""
    print("\n" + "=" * 50)
    print("📊 BENCHMARK RESULTS")
    print("=" * 50)

    for result in results:
        print(f"\n🔧 {result['operation'].replace('_', ' ').title()}:")
        if "error" in result:
            print(f"   ❌ Error: {result['error']}")
            continue

        for key, value in result.items():
            if key == "operation":
                continue
            if isinstance(value, float):
                if "per_sec" in key:
                    print(".2f")
                elif "time" in key:
                    print(".4f")
                else:
                    print(".2f")
            else:
                print(f"   {key}: {value}")


def main():
    """Main benchmark function."""
    results = run_benchmarks()
    print_results(results)

    # Check if any benchmarks failed
    failed = any("error" in r for r in results)
    if failed:
        print("\n⚠️  Some benchmarks failed - check output above")
        return 1
    else:
        print("\n✅ All benchmarks completed successfully")
        return 0


if __name__ == "__main__":
    sys.exit(main())
