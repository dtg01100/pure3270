#!/usr/bin/env python3
"""
Example: Using pure3270.P3270Client as a direct replacement for p3270.P3270Client.

This demonstrates how pure3270.P3270Client can be used as a drop-in replacement
for p3270.P3270Client without requiring any patching or monkey-patching.

Simply import pure3270.P3270Client instead of p3270.P3270Client.
"""

import argparse
import logging
import time

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    parser = argparse.ArgumentParser(
        description="Native P3270Client demonstration without patching."
    )
    parser.add_argument("--host", default="localhost", help="Host to connect to")
    parser.add_argument("--port", type=int, default=23, help="Port to connect to")
    parser.add_argument("--user", default="guest", help="Username for login")
    parser.add_argument("--password", default="guest", help="Password for login")
    parser.add_argument("--ssl", action="store_true", help="Use SSL connection")
    args = parser.parse_args()

    print("=== Pure3270 Native P3270Client Demo ===")
    print("This example shows how to use pure3270.P3270Client as a direct")
    print("replacement for p3270.P3270Client without any patching.\n")

    try:
        # Import pure3270 and use P3270Client directly
        from pure3270 import P3270Client

        print("✓ Imported pure3270.P3270Client successfully")

        # Create client using exact same API as p3270.P3270Client
        client = P3270Client(
            hostName=args.host,
            hostPort=str(args.port),  # p3270 takes string
            modelName="3279-4",
            enableTLS="yes" if args.ssl else "no",
            timeoutInSec=20,
        )

        print(f"✓ Created P3270Client for {client.hostName}:{client.hostPort}")
        print(f"  Model: {client.modelName}")
        print(f"  TLS: {client.enableTLS}")
        print(f"  Instance #{client.numOfInstances}")

        # Test methods that work without connection
        print(f"\n✓ isConnected(): {client.isConnected()}")
        print(f"✓ makeArgs(): {client.makeArgs()}")
        print(f"✓ getScreen() returns: {len(client.getScreen())} chars")

        # Demonstrate s3270 command compatibility
        print("\n--- S3270 Command Compatibility ---")
        commands = [
            "String(Hello World)",
            "Enter",
            "PF(1)",
            "MoveCursor(5,10)",
            "Clear",
            "NoOpCommand",
        ]

        for cmd in commands:
            try:
                client.send(cmd)
                print(f"✓ Sent s3270 command: {cmd}")
            except Exception as e:
                print(f"✗ Failed to send {cmd}: {e}")

        # Demonstrate high-level API methods
        print("\n--- High-Level API Methods ---")

        # Text input
        client.sendText("username_test")
        print("✓ sendText() works")

        # Key operations
        client.sendEnter()
        client.sendTab()
        client.sendPF(3)
        client.sendPA(1)
        print("✓ Key sending methods work")

        # Cursor movement
        client.moveTo(10, 20)
        client.moveCursorUp()
        client.moveCursorDown()
        client.moveCursorLeft()
        client.moveCursorRight()
        print("✓ Cursor movement methods work")

        # Screen operations
        client.clearScreen()
        screen_text = client.printScreen()
        print(f"✓ Screen operations work (screen: {len(screen_text)} chars)")

        # Text reading
        text_at_pos = client.readTextAtPosition(0, 0, 10)
        text_area = client.readTextArea(0, 0, 2, 10)
        found_text = client.foundTextAtPosition(0, 0, "test")
        print(f"✓ Text reading methods work")

        # Field operations
        client.delChar()
        client.delField()
        client.eraseChar()
        print("✓ Field operation methods work")

        # Wait operations (with short timeouts for demo)
        result1 = client.waitForOutput(0.1)
        result2 = client.waitFor3270Mode(0.1)
        result3 = client.waitForTimeout(0.1)
        print(f"✓ Wait operations work: {result1}, {result2}, {result3}")

        # Connection attempt (will likely fail without real host)
        print(f"\n--- Connection Test ---")
        try:
            print(f"Attempting to connect to {args.host}:{args.port}...")
            client.connect()
            print("✓ Connected successfully!")

            # If connected, try some operations
            client.sendText(args.user)
            client.sendEnter()
            time.sleep(1)

            client.sendText(args.password)
            client.sendEnter()
            time.sleep(1)

            screen = client.getScreen()
            print(f"Screen content: {screen[:100]}...")

        except Exception as e:
            print(f"✗ Connection failed (expected): {e}")
            print("  This is normal when connecting to non-existent hosts")

        finally:
            # Clean disconnect
            client.disconnect()
            print("✓ Disconnected cleanly")

        print("\n=== Comparison with p3270 ===")
        print("To use this instead of p3270, simply change:")
        print("  OLD: from p3270 import P3270Client")
        print("  NEW: from pure3270 import P3270Client")
        print("")
        print("No other code changes needed! The API is identical.")
        print("")
        print("Benefits of pure3270.P3270Client:")
        print("  ✓ No s3270 binary dependency")
        print("  ✓ Pure Python implementation")
        print("  ✓ No subprocess overhead")
        print("  ✓ Better error handling")
        print("  ✓ Identical API to p3270.P3270Client")
        print("  ✓ No monkey-patching required")

        print(f"\n🎉 Demo completed successfully!")

    except ImportError as e:
        print(f"✗ Import failed: {e}")
        print("Make sure pure3270 is installed: pip install -e .")
        return 1

    except Exception as e:
        print(f"✗ Demo failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
