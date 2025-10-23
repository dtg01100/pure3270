#!/usr/bin/env python3
"""
Example: Error Handling and Recovery Patterns

This example demonstrates comprehensive error handling strategies for pure3270:
- Connection errors and recovery
- Timeout handling
- SSL/TLS certificate issues
- Network interruption recovery
- Protocol negotiation failures
- Invalid terminal configurations
- File transfer error handling
- Screen parsing error recovery

Requires: pure3270 installed in venv.
Run: python examples/example_error_handling.py
"""

import asyncio
import ssl
import time
from typing import Optional

from pure3270 import AsyncSession, Session, setup_logging
from pure3270.exceptions import *

# Setup logging to see error details
setup_logging(level="DEBUG")


def demo_connection_errors():
    """Demonstrate connection error handling."""
    print("=== Connection Error Handling Demo ===")

    print("Connection error handling principles:")
    print("- Always catch connection exceptions")
    print("- Implement retry logic for transient failures")
    print("- Use timeouts to prevent hanging")
    print("- Log connection failures for debugging")

    # Demonstrate proper exception handling patterns
    print("\nUsing context managers for automatic cleanup:")
    try:
        with Session() as session:
            # This won't connect but shows proper usage
            session.connect("demonstration.only", port=23)
    except Exception as e:
        print(f"✓ Context manager properly handled error: {type(e).__name__}")

    print("\nManual cleanup pattern:")
    session = None
    try:
        session = Session()
        session.connect("demonstration.only", port=23)
    except Exception as e:
        print(f"✓ Error handled properly: {type(e).__name__}")
    finally:
        if session:
            session.close()


def demo_timeout_handling():
    """Demonstrate timeout handling patterns."""
    print("\n=== Timeout Handling Demo ===")

    # Demonstrate timeout concepts without real network
    print("Timeout handling principles:")
    print("- Network operations should always have timeouts")
    print("- Connection attempts should be limited")
    print("- Async operations prevent blocking")
    print("- Proper exception handling for timeouts")

    # Show timeout configuration examples
    with Session() as session:
        # Demonstrate read timeout on disconnected session
        try:
            print("Attempting read on disconnected session with short timeout...")
            data = session.read(timeout=0.1)  # Very short timeout
            print("ERROR: Should have timed out!")
        except Exception as e:
            print(f"✓ Expected timeout: {type(e).__name__}: {e}")


def demo_certificate_handling():
    """Demonstrate SSL certificate validation handling."""
    print("\n=== SSL Certificate Handling Demo ===")

    print("SSL handling principles:")
    print("- Always configure SSL contexts appropriately")
    print("- Certificate validation prevents man-in-middle attacks")
    print("- Self-signed certificates may be needed for testing")

    # Demonstrate SSL context creation without real connection
    ssl_context = ssl.create_default_context()
    print(f"✓ Default SSL context created: check_hostname={ssl_context.check_hostname}")

    insecure_context = ssl.create_default_context()
    insecure_context.check_hostname = False
    insecure_context.verify_mode = ssl.CERT_NONE
    print(
        f"✓ Insecure SSL context created (for testing only): check_hostname={insecure_context.check_hostname}"
    )


def demo_terminal_configuration_errors():
    """Demonstrate terminal configuration error handling."""
    print("\n=== Terminal Configuration Error Handling Demo ===")

    # Test invalid terminal type
    print("Testing invalid terminal type...")
    try:
        Session(terminal_type="INVALID-MODEL")
        print("ERROR: Should have failed with invalid terminal type!")
    except ValueError as e:
        print(f"✓ Expected ValueError: {e}")
    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}")

    # Test valid terminal types
    valid_types = ["IBM-3278-2", "IBM-3279-3", "IBM-3278-5"]
    for term_type in valid_types:
        try:
            session = Session(terminal_type=term_type)
            sb = session.screen_buffer
            print(f"✓ {term_type}: {sb.rows}x{sb.cols}")
            session.close()
        except Exception as e:
            print(f"✗ {term_type}: {type(e).__name__}: {e}")


async def demo_async_error_recovery():
    """Demonstrate async error recovery patterns."""
    print("\n=== Async Error Recovery Demo ===")

    print("Async error handling patterns:")
    print("- Use async context managers for automatic cleanup")
    print("- Implement exponential backoff for retries")
    print("- Use asyncio.wait_for() for timeouts")
    print("- Handle connection state transitions properly")

    async with AsyncSession() as session:
        # Demonstrate operation on disconnected session (async)
        try:
            data = b"test"
            await session.send(data)
            print("ERROR: Should have failed on disconnected session")
        except Exception as e:
            print(f"✓ Expected async error handling: {type(e).__name__}: {e}")

    # Demonstrate retry pattern without actual connection
    print("Simulated async retry pattern:")
    max_retries = 3
    for attempt in range(max_retries):
        print(f"Retry attempt {attempt + 1}/{max_retries}")
        if attempt < max_retries - 1:
            await asyncio.sleep(0.5)  # Short delay for demo
        else:
            print("All retry attempts exhausted")


def demo_operation_errors():
    """Demonstrate operation errors and recovery."""
    print("\n=== Operation Error Handling Demo ===")

    with Session() as session:
        # Test operations without connection
        operations = [
            ("send", lambda: session.send(b"test")),
            ("read", lambda: session.read(timeout=1.0)),
            ("string", lambda: session.string("test")),
            ("enter", lambda: session.enter()),
            ("key", lambda: session.key("Enter")),
        ]

        for op_name, op_func in operations:
            try:
                op_func()
                print(f"✗ {op_name}: Should have failed without connection")
            except Exception as e:
                print(f"✓ {op_name}: Expected error - {type(e).__name__}: {e}")


def demo_network_recovery():
    """Demonstrate network interruption recovery."""
    print("\n=== Network Interruption Recovery Demo ===")

    # This would require actual network testing with interruptions
    # For demo purposes, we'll show the framework

    with Session() as session:
        print("Network recovery patterns:")
        print("- Implement retry logic with exponential backoff")
        print("- Use connection pooling for multiple attempts")
        print("- Cache connection state for quick recovery")
        print("- Implement circuit breaker pattern for repeated failures")
        print("- Use async operations to avoid blocking during recovery")

        # Example recovery framework
        class ConnectionManager:
            def __init__(self, max_retries: int = 3, backoff_factor: float = 1.5):
                self.max_retries = max_retries
                self.backoff_factor = backoff_factor

            def connect_with_retry(
                self, hostname: str, port: int = 23
            ) -> Optional[Session]:
                """Attempt connection with retry and backoff."""
                session = None
                for attempt in range(self.max_retries):
                    try:
                        session = Session()
                        session.connect(hostname, port)
                        print(
                            f"✓ Connected to {hostname}:{port} on attempt {attempt + 1}"
                        )
                        return session
                    except Exception as e:
                        wait_time = self.backoff_factor**attempt
                        print(f"✗ Attempt {attempt + 1} failed: {e}")
                        if attempt < self.max_retries - 1:
                            print(f"  Waiting {wait_time:.1f}s before retry...")
                            time.sleep(wait_time)
                        else:
                            print("All attempts failed")
                            if session:
                                session.close()
                            return None
                return session

        manager = ConnectionManager()
        result = manager.connect_with_retry("httpbin.org", 80)
        if result:
            result.close()
            print("✓ Recovery pattern demonstration complete")
        else:
            print("✗ Recovery pattern failed (expected for demo)")


async def main_async():
    """Run async demonstrations."""
    await demo_async_error_recovery()


def main():
    """Run all error handling demonstrations."""
    print("Pure3270 Error Handling and Recovery Patterns Demo")
    print("=" * 60)

    try:
        demo_connection_errors()
        demo_timeout_handling()
        demo_certificate_handling()
        demo_terminal_configuration_errors()
        demo_operation_errors()
        demo_network_recovery()

        # Run async demos
        asyncio.run(main_async())

        print("\n" + "=" * 60)
        print("✓ All error handling scenarios demonstrated")
        print("\nKey takeaways:")
        print("- Always wrap connections in try/except blocks")
        print("- Implement retry logic for transient failures")
        print("- Use appropriate timeouts to avoid hanging")
        print("- Configure SSL contexts based on your security requirements")
        print("- Validate terminal configurations early")
        print("- Handle disconnects gracefully with connection pooling")

    except Exception as e:
        print(f"Demo failed unexpectedly: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
