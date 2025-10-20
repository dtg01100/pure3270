"""Pure3270 pub400.com connectivity test with ultra-fast timing profile.

Demonstrates using the P3270Client with aggressive timing profile to:
1. Connect to pub400.com with minimal delays
2. Send an Enter key
3. Read back the immediate screen buffer representation
4. Report detailed timing metrics

This test uses the ultra-fast timing profile for optimal connection performance.
"""

import logging
import time

from pure3270.p3270_client import P3270Client

# Configure logging to capture timing information
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

HOST = "pub400.com"
PORT = 23


def configure_ultra_fast_timing(client: P3270Client) -> None:
    """Configure the client for ultra-fast timing profile."""
    # Access the underlying session and handler to configure timing
    if hasattr(client, "_pure_session") and client._pure_session:
        session = client._pure_session
        if hasattr(session, "_async_session") and session._async_session:
            async_session = session._async_session
            if hasattr(async_session, "_handler") and async_session._handler:
                handler = async_session._handler

                # Configure aggressive timing profile (ultra-fast)
                handler.configure_timing_profile("aggressive")
                logger.info("✓ Configured aggressive timing profile")

                # Enable timing monitoring for detailed metrics
                handler.enable_timing_monitoring(True)
                logger.info("✓ Enabled timing monitoring")

                # Enable step delays for precise timing control
                handler.enable_step_delays(True)
                logger.info("✓ Enabled step delays")

                # Get current timing configuration
                current_profile = handler.get_current_timing_profile()
                timing_metrics = handler.get_timing_metrics()

                logger.info(f"✓ Current timing profile: {current_profile}")
                logger.info(f"✓ Timing configuration active: {bool(timing_metrics)}")


def main() -> int:
    """Main test function with ultra-fast timing."""
    print(f"🔥 Testing pub400.com connection with ULTRA-FAST timing profile...")
    print(f"📍 Target: {HOST}:{PORT}")
    print("=" * 60)

    # Record start time for total connection duration
    total_start_time = time.time()

    try:
        # Create client with connection parameters
        print("📡 Creating P3270Client...")
        client = P3270Client(hostName=HOST, hostPort=PORT)

        # Configure ultra-fast timing profile
        print("⚡ Configuring ultra-fast timing profile...")
        configure_ultra_fast_timing(client)

        # Record connection start time
        connection_start_time = time.time()

        print("🔌 Connecting to pub400.com...")
        client.connect()
        connection_end_time = time.time()

        connection_duration = connection_end_time - connection_start_time
        print(f"✅ Connected successfully in {connection_duration:.3f}s")

        # Record operation start time
        operation_start_time = time.time()

        print("⌨️  Sending Enter key...")
        client.sendEnter()

        print("📖 Reading screen response...")
        screen = client.getScreen()

        operation_end_time = time.time()
        operation_duration = operation_end_time - operation_start_time

        print("📊 Screen content received:")
        print("-" * 40)
        if screen.strip():
            # Show first few lines of screen content
            lines = screen.split("\n")
            for i, line in enumerate(lines[:10], 1):
                print(f"{i:2d}: {line}")
            total_lines = len(lines)
            if total_lines > 10:
                print(f"... ({total_lines - 10} more lines)")
        else:
            print("(Empty screen)")
        print("-" * 40)

        # Get timing metrics from handler
        if hasattr(client, "_pure_session") and client._pure_session:
            session = client._pure_session
            if hasattr(session, "_async_session") and session._async_session:
                async_session = session._async_session
                if hasattr(async_session, "_handler") and async_session._handler:
                    handler = async_session._handler
                    timing_metrics = handler.get_timing_metrics()

                    if timing_metrics:
                        print("⏱️  Timing Metrics:")
                        total_time = timing_metrics.get("total_negotiation_time", "N/A")
                        print(
                            f"   • Total negotiation time: {total_time:.3f}s"
                            if total_time != "N/A"
                            else "   • Total negotiation time: N/A"
                        )
                        print(
                            f"   • Steps completed: {timing_metrics.get('steps_completed', 'N/A')}"
                        )
                        print(
                            f"   • Timeouts occurred: {timing_metrics.get('timeouts_occurred', 'N/A')}"
                        )
                        print(
                            f"   • Delays applied: {timing_metrics.get('delays_applied', 'N/A')}"
                        )

                        if "step_timings" in timing_metrics:
                            print("   • Step breakdown:")
                            for step, duration in timing_metrics[
                                "step_timings"
                            ].items():
                                print(f"     - {step}: {duration:.3f}s")

        total_end_time = time.time()
        total_duration = total_end_time - total_start_time

        print("=" * 60)
        print("📈 Performance Summary:")
        print(f"   • Total test duration: {total_duration:.3f}s")
        print(f"   • Connection time: {connection_duration:.3f}s")
        print(f"   • Operation time: {operation_duration:.3f}s")
        print(f"   • Screen content length: {len(screen)} characters")

        # Calculate efficiency metrics
        if total_duration > 0:
            connection_efficiency = (connection_duration / total_duration) * 100
            operation_efficiency = (operation_duration / total_duration) * 100
            print(f"   • Connection efficiency: {connection_efficiency:.1f}%")
            print(f"   • Operation efficiency: {operation_efficiency:.1f}%")

        print("=" * 60)
        print("✅ Ultra-fast timing test completed successfully!")
        return 0

    except Exception as e:
        total_end_time = time.time()
        total_duration = total_end_time - total_start_time

        print("=" * 60)
        print("❌ Connection or negotiation failed:")
        print(f"   • Error: {e}")
        print(f"   • Total time elapsed: {total_duration:.3f}s")
        print("=" * 60)
        return 1

    finally:
        print("🔌 Closing session...")
        if "client" in locals():
            client.disconnect()
        print("✅ Session closed.")


if __name__ == "__main__":  # pragma: no cover - manual example
    raise SystemExit(main())
