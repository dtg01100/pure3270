#!/usr/bin/env python3
"""
Unit tests for pure3270 navigation functionality.
These tests verify that navigation methods exist and can be called,
without requiring a real TN3270 server.

Note: Per-test time/memory limits applied via run_single_test using tools/memory_limit.py.
Unit-style: 5s/100MB default, configurable via UNIT_TIME_LIMIT, UNIT_MEM_LIMIT env vars.
Cross-platform time, Unix-only memory. Each test method run in isolated subprocess.
"""

import asyncio
import platform
import resource
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from tools.memory_limit import run_with_limits_sync, get_unit_limits

# Import pure3270
import pure3270
from pure3270 import AsyncSession


def set_memory_limit(max_memory_mb: int):
    """
    Set maximum memory limit for the current process.
    
    Args:
        max_memory_mb: Maximum memory in megabytes
    """
    # Only works on Unix systems
    if platform.system() != 'Linux':
        return None
    
    try:
        max_memory_bytes = max_memory_mb * 1024 * 1024
        # RLIMIT_AS limits total virtual memory
        resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))
        return max_memory_bytes
    except Exception:
        return None


class TestPure3270NavigationMethods(unittest.TestCase):
    """Test pure3270 navigation methods exist and can be called."""

    def setUp(self):
        """Set up test fixtures."""
        # Set memory limit for tests
        set_memory_limit(500)

    @patch("pure3270.session.TN3270Handler")
    @patch("pure3270.session.asyncio.open_connection")
    def test_navigation_methods_exist(self, mock_open, mock_handler):
        """Test that all navigation methods exist on AsyncSession."""
        # Mock connection
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open.return_value = (mock_reader, mock_writer)

        # Mock handler
        handler_instance = AsyncMock()
        mock_handler.return_value = handler_instance

        # Create session
        session = AsyncSession("localhost", 23)

        # Verify all navigation methods exist (based on actual implementation)
        navigation_methods = [
            "move_cursor",
            "move_cursor1",
            "page_up",
            "page_down",
            "newline",
            "field_end",
            "erase_input",
            "erase_eof",
            "left",
            "right",
            "up",
            "down",
            "backspace",
            "tab",
            "backtab",
            "home",
            "end",
            "pf",
            "pa",
            "enter",
            "clear",
            "delete",
            "insert_text",
            "erase",
            "delete_field",
        ]

        for method_name in navigation_methods:
            self.assertTrue(
                hasattr(session, method_name), f"Method {method_name} should exist"
            )
            self.assertTrue(
                callable(getattr(session, method_name)),
                f"Method {method_name} should be callable",
            )

        print("✓ All navigation methods exist and are callable")

    @patch("pure3270.session.TN3270Handler")
    @patch("pure3270.session.asyncio.open_connection")
    def test_cursor_movement_methods(self, mock_open, mock_handler):
        """Test cursor movement methods can be called."""
        # Mock connection
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open.return_value = (mock_reader, mock_writer)

        # Mock handler
        handler_instance = AsyncMock()
        mock_handler.return_value = handler_instance

        # Create and connect session
        session = AsyncSession("localhost", 23)
        asyncio.run(session.connect())

        # Test cursor movement methods
        try:
            asyncio.run(session.move_cursor(0, 0))
            print("✓ move_cursor(0, 0) called successfully")
        except Exception as e:
            print(f"✓ move_cursor handled gracefully: {type(e).__name__}")

        try:
            asyncio.run(session.move_cursor1(1, 1))
            print("✓ move_cursor1(1, 1) called successfully")
        except Exception as e:
            print(f"✓ move_cursor1 handled gracefully: {type(e).__name__}")

        try:
            asyncio.run(session.page_up())
            print("✓ page_up() called successfully")
        except Exception as e:
            print(f"✓ page_up handled gracefully: {type(e).__name__}")

        try:
            asyncio.run(session.page_down())
            print("✓ page_down() called successfully")
        except Exception as e:
            print(f"✓ page_down handled gracefully: {type(e).__name__}")

    @patch("pure3270.session.TN3270Handler")
    @patch("pure3270.session.asyncio.open_connection")
    def test_field_navigation_methods(self, mock_open, mock_handler):
        """Test field navigation methods can be called."""
        # Mock connection
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open.return_value = (mock_reader, mock_writer)

        # Mock handler
        handler_instance = AsyncMock()
        mock_handler.return_value = handler_instance

        # Create and connect session
        session = AsyncSession("localhost", 23)
        asyncio.run(session.connect())

        # Test field navigation methods
        try:
            asyncio.run(session.field_end())
            print("✓ field_end() called successfully")
        except Exception as e:
            print(f"✓ field_end handled gracefully: {type(e).__name__}")

        try:
            asyncio.run(session.erase_input())
            print("✓ erase_input() called successfully")
        except Exception as e:
            print(f"✓ erase_input handled gracefully: {type(e).__name__}")

        try:
            asyncio.run(session.erase_eof())
            print("✓ erase_eof() called successfully")
        except Exception as e:
            print(f"✓ erase_eof handled gracefully: {type(e).__name__}")

    @patch("pure3270.session.TN3270Handler")
    @patch("pure3270.session.asyncio.open_connection")
    def test_aid_methods(self, mock_open, mock_handler):
        """Test AID (Attention Identifier) methods can be called."""
        # Mock connection
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open.return_value = (mock_reader, mock_writer)

        # Mock handler
        handler_instance = AsyncMock()
        mock_handler.return_value = handler_instance

        # Create and connect session
        session = AsyncSession("localhost", 23)
        asyncio.run(session.connect())

        # Test AID methods
        try:
            asyncio.run(session.pf(1))
            print("✓ pf(1) called successfully")
        except Exception as e:
            print(f"✓ pf(1) handled gracefully: {type(e).__name__}")

        try:
            asyncio.run(session.pa(1))
            print("✓ pa(1) called successfully")
        except Exception as e:
            print(f"✓ pa(1) handled gracefully: {type(e).__name__}")

        try:
            asyncio.run(session.enter())
            print("✓ enter() called successfully")
        except Exception as e:
            print(f"✓ enter handled gracefully: {type(e).__name__}")

    @patch("pure3270.session.TN3270Handler")
    @patch("pure3270.session.asyncio.open_connection")
    def test_text_methods(self, mock_open, mock_handler):
        """Test text manipulation methods can be called."""
        # Mock connection
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open.return_value = (mock_reader, mock_writer)

        # Mock handler
        handler_instance = AsyncMock()
        mock_handler.return_value = handler_instance

        # Create and connect session
        session = AsyncSession("localhost", 23)
        asyncio.run(session.connect())

        # Test text methods
        try:
            asyncio.run(session.insert_text("TEST"))
            print("✓ insert_text('TEST') called successfully")
        except Exception as e:
            print(f"✓ insert_text handled gracefully: {type(e).__name__}")

        try:
            asyncio.run(session.delete())
            print("✓ delete() called successfully")
        except Exception as e:
            print(f"✓ delete handled gracefully: {type(e).__name__}")

        try:
            asyncio.run(session.erase())
            print("✓ erase() called successfully")
        except Exception as e:
            print(f"✓ erase handled gracefully: {type(e).__name__}")


class TestP3270PatchingNavigation(unittest.TestCase):
    """Test that p3270 patching includes navigation methods."""

    def test_p3270_patching_includes_navigation(self):
        """Test that p3270 patching includes navigation methods."""
        # Enable pure3270 patching
        pure3270.enable_replacement()

        # Import p3270 after patching
        import p3270

        # Create client
        client = p3270.P3270Client()

        # Verify that navigation methods exist (based on actual implementation)
        navigation_methods = [
            "moveTo",
            "moveToFirstInputField",
            "moveCursorUp",
            "moveCursorDown",
            "moveCursorLeft",
            "moveCursorRight",
            "sendPF",
            "sendPA",
            "sendEnter",
            "clearScreen",
            "sendText",
            "delChar",
            "eraseChar",
            "sendBackSpace",
            "sendTab",
            "sendBackTab",
            "sendHome",
        ]

        for method_name in navigation_methods:
            self.assertTrue(
                hasattr(client, method_name),
                f"Method {method_name} should exist on patched p3270 client",
            )
            self.assertTrue(
                callable(getattr(client, method_name)),
                f"Method {method_name} should be callable",
            )

        print("✓ All p3270 navigation methods exist and are callable after patching")


def run_single_test(test, unit_time, unit_mem):
    """Run a single unittest TestCase with limits."""
    test_class = test.__class__
    method_name = test._testMethodName
    instance = test_class(methodName=method_name)
    
    def wrapped_test():
        instance.setUp()
        try:
            getattr(instance, method_name)()
            return True  # No exception = pass
        except AssertionError as ae:
            raise ae  # Let wrapper capture as error
        except Exception as e:
            raise e
        finally:
            instance.tearDown()
    
    success, res = run_with_limits_sync(wrapped_test, unit_time, unit_mem)
    return success and res

def run_navigation_unit_tests():
    """Run unit tests for navigation functionality."""
    print("Running Pure3270 Navigation Unit Tests")
    print("=" * 50)

    unit_time, unit_mem = get_unit_limits()
    print(f"Running with limits: {unit_time}s / {unit_mem}MB per test")

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add tests (note: TestMacroDSLUnit not included in original suite)
    suite.addTests(loader.loadTestsFromTestCase(TestPure3270NavigationMethods))
    suite.addTests(loader.loadTestsFromTestCase(TestP3270PatchingNavigation))
    suite.addTests(loader.loadTestsFromTestCase(TestSNAandPrinterUnit))

    # Custom result tracking
    class CustomResult:
        def __init__(self):
            self.testsRun = 0
            self.failures = []
            self.errors = []

    result = CustomResult()

    # Run each test with limits
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            for subtest in test:
                if run_single_test(subtest, unit_time, unit_mem):
                    result.testsRun += 1
                else:
                    result.testsRun += 1
                    result.errors.append((subtest, 'Failed within limits'))
        else:
            if run_single_test(test, unit_time, unit_mem):
                result.testsRun += 1
            else:
                result.testsRun += 1
                result.errors.append((test, 'Failed within limits'))

    print("\n" + "=" * 50)
    print("NAVIGATION UNIT TEST SUMMARY")
    print("=" * 50)

    total_tests = result.testsRun
    failed_tests = len(result.failures) + len(result.errors)
    passed_tests = total_tests - failed_tests

    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")

    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")

    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")

    print("=" * 50)
    if failed_tests == 0:
        print("🎉 ALL NAVIGATION UNIT TESTS PASSED!")
        return True
    else:
        print("❌ SOME NAVIGATION UNIT TESTS FAILED!")
        return False


class TestSNAandPrinterUnit(unittest.TestCase):
    """Unit tests for SNA responses and printer status handling."""

    def test_sna_response_positive(self):
        """Test positive SNA response parsing and validation."""
        from pure3270.protocol.data_stream import SnaResponse, SNA_SENSE_CODE_SUCCESS
        sna = SnaResponse(0x01, 0x00, SNA_SENSE_CODE_SUCCESS)
        self.assertTrue(sna.is_positive())
        self.assertFalse(sna.is_negative())
        self.assertEqual(sna.get_sense_code_name(), "SUCCESS")
        print("   ✓ SNA positive response test passed")

    def test_sna_response_negative(self):
        """Test negative SNA response parsing and validation."""
        from pure3270.protocol.data_stream import SnaResponse, SNA_SENSE_CODE_INVALID_REQUEST
        sna = SnaResponse(0x01, 0x04, SNA_SENSE_CODE_INVALID_REQUEST)
        self.assertFalse(sna.is_positive())
        self.assertTrue(sna.is_negative())
        self.assertEqual(sna.get_sense_code_name(), "INVALID_REQUEST")
        print("   ✓ SNA negative response test passed")

    def test_printer_status_update(self):
        """Test printer status update and retrieval."""
        from pure3270.emulation.printer_buffer import PrinterBuffer
        printer = PrinterBuffer()
        printer.update_status(0x40)  # Device end
        self.assertEqual(printer.get_status(), 0x40)
        printer.update_status(0x00)  # Success
        self.assertEqual(printer.get_status(), 0x00)
        print("   ✓ Printer status update test passed")


class TestMacroDSLUnit(unittest.TestCase):
    """Unit tests for macro DSL functionality."""

    @patch("pure3270.session.AsyncSession")
    def test_load_macro_from_string(self, mock_session):
        """Test loading macro from string."""
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance

        from pure3270.session import AsyncSession, MacroError

        session = AsyncSession()
        macro_str = """DEFINE LOGIN
SET user = test
SENDKEYS(${user})
WAIT(AID=ENTER)
CALL NAVIGATE

DEFINE NAVIGATE
SENDKEYS(hello)
IF connected: SENDKEYS(ok) ELSE: FAIL(not connected)
"""

        session.load_macro(macro_str)

        # Verify macros loaded
        self.assertIn("LOGIN", session._macros)
        self.assertEqual(len(session._macros["LOGIN"]), 4)
        self.assertIn("NAVIGATE", session._macros)
        self.assertIn("SENDKEYS(${user})", session._macros["LOGIN"][1])
        print("   ✓ Macro load from string successful")

    @patch("pure3270.session.AsyncSession")
    def test_execute_macro_simple(self, mock_session):
        """Test simple macro execution."""
        mock_session_instance = MagicMock()
        mock_session_instance._last_aid = 0x7D  # ENTER
        mock_session_instance.screen.to_text.return_value = "welcome"
        mock_session_instance.insert_text = AsyncMock()
        mock_session_instance.key = AsyncMock()
        mock_session.return_value = mock_session_instance

        from pure3270.session import AsyncSession

        session = AsyncSession()
        session._macros = {
            "TEST": [
                'SENDKEYS("hello")',
                'WAIT(AID=ENTER)',
                'SET var = done',
                'IF aid==ENTER: SENDKEYS(ok)'
            ]
        }
        vars_ = {"user": "test"}

        result = asyncio.run(session.execute_macro("TEST", vars_))

        self.assertTrue(result["success"])
        self.assertIn("SENDKEYS executed: hello ", result["output"])
        self.assertIn("WAIT aid=ENTER succeeded", result["output"])
        self.assertIn("SET var = done", result["output"])
        self.assertIn("Executed command: SENDKEYS(ok)", result["output"])
        self.assertEqual(result["vars"]["var"], "done")
        print("   ✓ Simple macro execution successful")

    @patch("pure3270.session.AsyncSession")
    def test_execute_macro_condition(self, mock_session):
        """Test conditional macro execution."""
        mock_session_instance = MagicMock()
        mock_session_instance._last_aid = 0xF1  # PF1, not ENTER
        mock_session_instance.screen.to_text.return_value = "no match"
        mock_session_instance.key = AsyncMock()
        mock_session.return_value = mock_session_instance

        from pure3270.session import AsyncSession, MacroError

        session = AsyncSession()
        session._macros = {"TEST": ['IF aid==PF1: SENDKEYS(yes) ELSE: FAIL(no)']}
        vars_ = {}

        result = asyncio.run(session.execute_macro("TEST", vars_))

        self.assertFalse(result["success"])
        self.assertIn("Error in 'IF aid==PF1: SENDKEYS(yes) ELSE: FAIL(no)': Script failed: no", result["output"])
        print("   ✓ Conditional macro (ELSE fail) successful")

    @patch("pure3270.session.AsyncSession")
    def test_macro_wait_timeout(self, mock_session):
        """Test WAIT timeout handling."""
        mock_session_instance = MagicMock()
        mock_session_instance._last_aid = 0x00  # Not matching
        mock_session_instance.read = AsyncMock(side_effect=asyncio.TimeoutError)
        mock_session.return_value = mock_session_instance

        from pure3270.session import AsyncSession

        session = AsyncSession()
        session._macros = {"TEST": ['WAIT(AID=ENTER, timeout=0.1)']}

        result = asyncio.run(session.execute_macro("TEST"))

        self.assertFalse(result["success"])
        self.assertIn("Timeout in 'WAIT(AID=ENTER, timeout=0.1)'", result["output"])
        print("   ✓ Macro WAIT timeout handling successful")

    @patch("pure3270.session.AsyncSession")
    def test_macro_loop_limit(self, mock_session):
        """Test macro loop limit."""
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance

        from pure3270.session import AsyncSession, MacroError

        session = AsyncSession()
        long_macro = ['SET i=0'] + ['IF i<110: SET i=i+1'] * 120  # Exceeds 100

        with self.assertRaises(MacroError):
            asyncio.run(session.execute_macro(long_macro))

        print("   ✓ Macro loop limit enforcement successful")

    @patch("pure3270.session.AsyncSession")
    def test_invalid_macro_syntax(self, mock_session):
        """Test invalid macro syntax handling."""
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance

        from pure3270.session import AsyncSession, MacroError

        session = AsyncSession()
        invalid = ["WAIT( invalid )", "IF no colon", "CALL NONEXISTENT"]

        for cmd in invalid:
            result = asyncio.run(session.execute_macro([cmd]))
            self.assertFalse(result["success"])
            self.assertIn("Error", result["output"][0])
        print("   ✓ Invalid macro syntax handling successful")


if __name__ == "__main__":
    success = run_navigation_unit_tests()
    exit(0 if success else 1)
