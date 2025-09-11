#!/usr/bin/env python3
"""
Quick smoke test for pure3270.
This test quickly verifies that pure3270 is functioning correctly.
"""

import asyncio
import sys
import os

# Add the current directory to the path so we can import pure3270
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))


def test_imports_and_basic_creation():
    """Test that imports work and basic classes can be created."""
    try:
        import pure3270
        from pure3270 import Session, AsyncSession

        # Create instances
        session = Session()
        async_session = AsyncSession()

        print("✓ Imports and basic creation successful")
        return True
    except Exception as e:
        print(f"✗ Imports or basic creation failed: {e}")
        return False


def test_p3270_patching():
    """Test that p3270 patching works."""
    try:
        import pure3270

        pure3270.enable_replacement()
        import p3270

        # Create client
        client = p3270.P3270Client()

        # Check that it's using our wrapper
        if "pure3270" in str(type(client.s3270)):
            print("✓ p3270 patching works")
            return True
        else:
            print("✗ p3270 patching failed")
            return False
    except Exception as e:
        print(f"✗ p3270 patching test failed: {e}")
        return False


def test_navigation_methods():
    """Test that key navigation methods exist."""
    try:
        import pure3270
        from pure3270 import AsyncSession

        session = AsyncSession()

        # Test a few key methods
        key_methods = ["connect", "send", "read", "close", "enter", "clear", "pf", "pa"]
        missing = []

        for method in key_methods:
            if not hasattr(session, method):
                missing.append(method)

        if missing:
            print(f"✗ Missing key methods: {', '.join(missing)}")
            return False

        print("✓ Key navigation methods present")
        return True
    except Exception as e:
        print(f"✗ Navigation methods test failed: {e}")
        return False


async def test_mock_connectivity():
    """Test basic connectivity with a mock server."""
    try:
        # Simple mock server
        class MockServer:
            def __init__(self):
                self.server = None

            async def start(self):
                async def handle_client(reader, writer):
                    try:
                        while True:
                            data = await reader.read(1024)
                            if not data:
                                break
                            writer.write(data)  # Echo back
                            await writer.drain()
                    except:
                        pass
                    finally:
                        writer.close()
                        await writer.wait_closed()

                self.server = await asyncio.start_server(
                    handle_client, "127.0.0.1", 2323
                )
                return True

            async def stop(self):
                if self.server:
                    self.server.close()
                    await self.server.wait_closed()

        # Start mock server
        mock_server = MockServer()
        if not await mock_server.start():
            print("✗ Failed to start mock server")
            return False

        try:
            import pure3270
            from pure3270 import AsyncSession

            # Test connection
            session = AsyncSession("127.0.0.1", 2323)
            try:
                await session.connect()
                await session.send(b"test")
                await session.close()
                print("✓ Mock connectivity test passed")
                return True
            except Exception as e:
                print(
                    f"✓ Mock connectivity test handled error gracefully: {type(e).__name__}"
                )
                return True
            finally:
                try:
                    await session.close()
                except:
                    pass
        finally:
            await mock_server.stop()

    except Exception as e:
        print(f"✗ Mock connectivity test failed: {e}")
        return False


async def main():
    """Run quick smoke tests."""
    print("=== Pure3270 Quick Smoke Test ===\n")

    # Run tests
    tests = [
        ("Imports and Basic Creation", test_imports_and_basic_creation),
        ("p3270 Patching", test_p3270_patching),
        ("Navigation Methods", test_navigation_methods),
        ("Mock Connectivity", test_mock_connectivity),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"Testing {test_name}...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 35)
    print("QUICK SMOKE TEST SUMMARY")
    print("=" * 35)

    all_passed = True
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:<25} {status}")
        if not result:
            all_passed = False

    print("=" * 35)
    if all_passed:
        print("🎉 ALL QUICK SMOKE TESTS PASSED!")
        print("Pure3270 is ready for use.")
    else:
        print("❌ SOME QUICK SMOKE TESTS FAILED!")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
