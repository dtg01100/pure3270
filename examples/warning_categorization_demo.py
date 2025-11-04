#!/usr/bin/env python3
"""
Pure3270 Warning Categorization Example

This example demonstrates how to use the warning categorization system
in a typical Pure3270 application, showing the benefits of categorized
warnings for debugging and production monitoring.
"""

import asyncio
import logging
import sys
from typing import Optional

# Import Pure3270 warning categorization
from pure3270.warnings import (
    WarningCategory,
    create_production_filter,
    create_protocol_filter,
    get_categorized_logger,
    get_warning_statistics,
    setup_default_warning_filters,
)


class ExampleTN3270Client:
    """
    Example TN3270 client demonstrating categorized warnings.
    """

    def __init__(self, environment: str = "development"):
        """Initialize the client with environment-specific warning configuration."""

        # Configure warnings based on environment
        setup_default_warning_filters(environment)

        # Create categorized logger
        self.logger = get_categorized_logger("example_client")

        # Store configuration
        self.environment = environment
        self.connected = False
        self.terminal_type = "IBM-3278-2"
        self.host = None

        self.logger.info(
            WarningCategory.CONFIGURATION,
            f"Example TN3270 Client initialized for {environment} environment",
        )

    async def connect(self, host: str, port: int = 23) -> bool:
        """Connect to TN3270 server with categorized error handling."""

        self.host = f"{host}:{port}"

        try:
            self.logger.info(WarningCategory.NETWORK, f"Connecting to {self.host}...")

            # Simulate connection logic
            await asyncio.sleep(0.1)  # Simulate network delay

            # Simulate various connection issues that would generate different warning types
            if host == "nonexistent.example.com":
                self.logger.log_network_warning(f"Cannot resolve hostname: {host}")
                return False

            elif port == 23 and host == "secure.example.com":
                self.logger.log_security_warning(
                    "Connecting to port 23 without encryption"
                )
                # Continue anyway for demonstration

            elif "slow" in host:
                self.logger.log_performance_warning(
                    "Host appears to be slow, may timeout"
                )
                await asyncio.sleep(0.5)  # Simulate slow response

            self.connected = True
            self.logger.info(
                WarningCategory.NETWORK, f"Successfully connected to {self.host}"
            )
            return True

        except ConnectionError as e:
            self.logger.log_network_warning(f"Connection failed to {self.host}: {e}")
            return False
        except Exception as e:
            self.logger.log_protocol_warning(f"Unexpected connection error: {e}")
            return False

    def set_terminal_type(self, terminal_type: str) -> None:
        """Set terminal type with validation and categorized warnings."""

        valid_types = ["IBM-3278-2", "IBM-3278-4", "IBM-3287-1"]

        if terminal_type not in valid_types:
            self.logger.log_configuration_warning(
                f"Invalid terminal type '{terminal_type}', "
                f"valid types are: {', '.join(valid_types)}. "
                f"Using default '{self.terminal_type}'"
            )
            # Continue with default
        else:
            old_type = self.terminal_type
            self.terminal_type = terminal_type
            self.logger.info(
                WarningCategory.CONFIGURATION,
                f"Terminal type changed: {old_type} -> {terminal_type}",
            )

    async def negotiate_protocol(self) -> bool:
        """Perform protocol negotiation with detailed categorization."""

        if not self.connected:
            self.logger.log_state_management_warning("Cannot negotiate: not connected")
            return False

        self.logger.info(
            WarningCategory.PROTOCOL_NEGOTIATION,
            "Starting TN3270E protocol negotiation...",
        )

        try:
            # Simulate protocol negotiation steps
            await asyncio.sleep(0.1)

            # Simulate various negotiation issues
            scenarios = [
                ("timeout", lambda: self._simulate_timeout()),
                ("malformed", lambda: self._simulate_malformed_response()),
                ("unsupported", lambda: self._simulate_unsupported_feature()),
                ("success", lambda: self._simulate_successful_negotiation()),
            ]

            # Choose scenario based on host (for demonstration)
            if self.host:
                for scenario_name, scenario_func in scenarios:
                    if scenario_name in self.host.lower():
                        return await scenario_func()

            return await self._simulate_successful_negotiation()

        except Exception as e:
            self.logger.log_protocol_warning(f"Protocol negotiation failed: {e}")
            return False

    async def _simulate_timeout(self) -> bool:
        """Simulate a negotiation timeout."""
        self.logger.log_timeout_warning("Protocol negotiation timeout after 30 seconds")
        return False

    async def _simulate_malformed_response(self) -> bool:
        """Simulate receiving malformed protocol data."""
        self.logger.log_data_stream_warning("Received malformed TN3270E response data")
        self.logger.log_parsing_warning("Failed to parse device type response")
        return False

    async def _simulate_unsupported_feature(self) -> bool:
        """Simulate server rejecting a feature."""
        self.logger.log_protocol_warning("Server rejected TN3270E enhanced data stream")
        self.logger.log_protocol_warning("Falling back to basic TN3270 mode")
        return True  # Fallback successful

    async def _simulate_successful_negotiation(self) -> bool:
        """Simulate successful negotiation."""
        self.logger.info(
            WarningCategory.PROTOCOL_NEGOTIATION,
            "TN3270E negotiation completed successfully",
        )
        self.logger.info(
            WarningCategory.PROTOCOL_NEGOTIATION,
            f"Negotiated terminal type: {self.terminal_type}",
        )
        return True

    async def send_data(self, data: str) -> bool:
        """Send data with categorized error handling."""

        if not self.connected:
            self.logger.log_state_management_warning("Cannot send data: not connected")
            return False

        try:
            # Simulate data transmission
            self.logger.debug(
                WarningCategory.PROTOCOL_NEGOTIATION, f"Sending data: {data[:50]}..."
            )

            if len(data) > 1000:
                self.logger.log_performance_warning(
                    f"Large data payload: {len(data)} bytes"
                )

            await asyncio.sleep(0.05)  # Simulate transmission time

            # Simulate various transmission issues
            if "error" in data.lower():
                self.logger.log_protocol_warning("Simulated transmission error")
                return False

            self.logger.debug(
                WarningCategory.PROTOCOL_NEGOTIATION, "Data sent successfully"
            )
            return True

        except Exception as e:
            self.logger.log_network_warning(f"Data transmission failed: {e}")
            return False

    def demonstrate_warning_categorization(self) -> None:
        """Demonstrate different warning categories in action."""

        print("\n" + "=" * 60)
        print("DEMONSTRATING WARNING CATEGORIZATION")
        print("=" * 60)

        # Protocol warnings
        print("\n📡 PROTOCOL WARNINGS (Critical - Protocol Issues):")
        self.logger.log_protocol_warning("TN3270E negotiation timeout")
        self.logger.log_protocol_warning("Unsupported TN3270E function requested")
        self.logger.log_protocol_warning("Malformed screen data received")

        # Configuration warnings
        print("\n⚙️ CONFIGURATION WARNINGS (Framework - Configuration Issues):")
        self.logger.log_configuration_warning("Invalid screen size, using 24x80")
        self.logger.log_configuration_warning("Missing terminal type, using default")
        self.logger.log_configuration_warning("Deprecated API call detected")

        # Security warnings
        print("\n🔒 SECURITY WARNINGS (Critical - Security Issues):")
        self.logger.log_security_warning("SSL certificate verification disabled")
        self.logger.log_security_warning("Connecting to unsecured port 23")
        self.logger.log_security_warning("Weak cipher suite in use")

        # Network warnings
        print("\n🌐 NETWORK WARNINGS (Integration - Network Issues):")
        self.logger.log_network_warning("Connection timeout to host")
        self.logger.log_network_warning("High latency detected")
        self.logger.log_network_warning("Packet loss detected")

        # Performance warnings
        print("\n⚡ PERFORMANCE WARNINGS (Performance - Optimization):")
        self.logger.log_performance_warning("Slow screen updates detected")
        self.logger.log_performance_warning("Memory usage high")
        self.logger.log_performance_warning("Inefficient data formatting")

        # State management warnings
        print("\n🔄 STATE WARNINGS (Framework - State Management):")
        self.logger.log_state_management_warning("Invalid state transition attempted")
        self.logger.log_state_management_warning("Session cleanup required")

        # Data stream warnings
        print("\n📊 DATA STREAM WARNINGS (Protocol - Data Issues):")
        self.logger.log_data_stream_warning("Unexpected data format")
        self.logger.log_data_stream_warning("Incomplete TN3270 command")
        self.logger.log_unknown_data_warning("Unrecognized structured field type")

        print("\n" + "=" * 60)
        print("✅ All warning categories demonstrated!")
        print("=" * 60)


async def main():
    """Run the warning categorization demonstration."""

    print("Pure3270 Warning Categorization Example")
    print("========================================")

    # Show current configuration
    stats = get_warning_statistics()
    print(f"\nCurrent warning configuration:")
    print(f"  Total categories: {stats['total_categories']}")
    print(f"  Enabled: {len(stats['enabled_categories'])}")
    print(f"  Disabled: {len(stats['disabled_categories'])}")

    # Test different environments
    environments = ["development", "production", "protocol_debug"]

    for env in environments:
        print(f"\n" + "=" * 50)
        print(f"TESTING {env.upper()} ENVIRONMENT")
        print("=" * 50)

        client = ExampleTN3270Client(env)

        # Demonstrate connection scenarios
        test_hosts = [
            f"good.{env}.example.com",
            f"timeout.{env}.example.com",
            f"malformed.{env}.example.com",
            f"unsupported.{env}.example.com",
        ]

        for host in test_hosts:
            print(f"\n🔌 Testing connection to {host}...")
            success = await client.connect(host)

            if success:
                await client.negotiate_protocol()
                await client.send_data(f"Test data for {host}")

        # Demonstrate configuration warnings
        print(f"\n⚙️ Testing configuration validation...")
        client.set_terminal_type("INVALID-TYPE")  # Will trigger configuration warning
        client.set_terminal_type("IBM-3278-4")  # Valid type

        # Show categorized warnings
        client.demonstrate_warning_categorization()

    print(f"\n🎉 Warning categorization demonstration completed!")
    print(f"\nKey Benefits Demonstrated:")
    print(f"  ✅ Clear distinction between protocol vs framework issues")
    print(f"  ✅ Environment-specific filtering (development vs production)")
    print(f"  ✅ Actionable warning messages with context")
    print(f"  ✅ Easy identification of critical vs non-critical issues")
    print(f"  ✅ Better debugging through categorized output")


if __name__ == "__main__":
    asyncio.run(main())
