#!/usr/bin/env python3
"""
Example of using Pure3270's high-level printer session API.

This demonstrates how to connect to a TN3270E printer LU and handle
SCS data streams from IBM mainframe systems.
"""

import asyncio
import logging

from pure3270 import AsyncPrinterSession, PrinterSession, setup_logging

# Setup logging
setup_logging("INFO")


def synchronous_printer_example() -> None:
    """Example using synchronous PrinterSession."""
    print("=== Synchronous Printer Session Example ===")

    try:
        with PrinterSession(host="printer-host.example.com", port=23) as session:
            print("Connected to printer host")

            # Wait for printer data (in a real scenario, this would be event-driven)
            import time

            time.sleep(5)  # Simulate waiting for print job

            # Get printer output
            output = session.get_printer_output()
            if output:
                print("Printer output:")
                print(output)
            else:
                print("No printer output received")

            # Get printer status
            status = session.get_printer_status()
            print(f"Printer status: 0x{status:02x}")

            # Get job statistics
            stats = session.get_job_statistics()
            print(f"Job statistics: {stats}")

    except Exception as e:
        print(f"Error: {e}")


async def asynchronous_printer_example() -> None:
    """Example using asynchronous AsyncPrinterSession."""
    print("\n=== Asynchronous Printer Session Example ===")

    try:
        async with AsyncPrinterSession(
            host="printer-host.example.com", port=23
        ) as session:
            print("Connected to printer host")

            # Wait for printer data
            await asyncio.sleep(5)  # Simulate waiting for print job

            # Get printer output
            output = await session.get_printer_output()
            if output:
                print("Printer output:")
                print(output)
            else:
                print("No printer output received")

            # Get printer status
            status = await session.get_printer_status()
            print(f"Printer status: 0x{status:02x}")

            # Get job statistics
            stats = await session.get_job_statistics()
            print(f"Job statistics: {stats}")

    except Exception as e:
        print(f"Error: {e}")


def main() -> None:
    """Run both examples."""
    print("Pure3270 Printer Session Examples")
    print("=================================")

    # Synchronous example
    synchronous_printer_example()

    # Asynchronous example
    asyncio.run(asynchronous_printer_example())

    print("\nExamples completed.")


if __name__ == "__main__":
    main()
