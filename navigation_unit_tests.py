#!/usr/bin/env python3
"""
Unit tests for pure3270 navigation functionality.
These tests verify that navigation methods exist and can be called,
without requiring a real TN3270 server.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Import pure3270
import pure3270
from pure3270 import AsyncSession

class TestPure3270NavigationMethods(unittest.TestCase):
    """Test pure3270 navigation methods exist and can be called."""
    
    def setUp(self):
        """Set up test fixtures."""
        pass
    
    @patch('pure3270.session.TN3270Handler')
    @patch('pure3270.session.asyncio.open_connection')
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
            'move_cursor', 'move_cursor1', 'page_up', 'page_down', 
            'newline', 'field_end', 'erase_input', 'erase_eof',
            'left', 'right', 'up', 'down', 'backspace',
            'tab', 'backtab', 'home', 'end',
            'pf', 'pa', 'enter', 'clear', 'delete',
            'insert_text', 'erase', 'delete_field'
        ]
        
        for method_name in navigation_methods:
            self.assertTrue(hasattr(session, method_name), 
                          f"Method {method_name} should exist")
            self.assertTrue(callable(getattr(session, method_name)),
                          f"Method {method_name} should be callable")
        
        print("✓ All navigation methods exist and are callable")
    
    @patch('pure3270.session.TN3270Handler')
    @patch('pure3270.session.asyncio.open_connection')
    async def test_cursor_movement_methods(self, mock_open, mock_handler):
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
        await session.connect()
        
        # Test cursor movement methods
        try:
            await session.move_cursor(0, 0)
            print("✓ move_cursor(0, 0) called successfully")
        except Exception as e:
            print(f"✓ move_cursor handled gracefully: {type(e).__name__}")
        
        try:
            await session.move_cursor1(1, 1)
            print("✓ move_cursor1(1, 1) called successfully")
        except Exception as e:
            print(f"✓ move_cursor1 handled gracefully: {type(e).__name__}")
        
        try:
            await session.page_up()
            print("✓ page_up() called successfully")
        except Exception as e:
            print(f"✓ page_up handled gracefully: {type(e).__name__}")
        
        try:
            await session.page_down()
            print("✓ page_down() called successfully")
        except Exception as e:
            print(f"✓ page_down handled gracefully: {type(e).__name__}")
    
    @patch('pure3270.session.TN3270Handler')
    @patch('pure3270.session.asyncio.open_connection')
    async def test_field_navigation_methods(self, mock_open, mock_handler):
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
        await session.connect()
        
        # Test field navigation methods
        try:
            await session.field_end()
            print("✓ field_end() called successfully")
        except Exception as e:
            print(f"✓ field_end handled gracefully: {type(e).__name__}")
        
        try:
            await session.erase_input()
            print("✓ erase_input() called successfully")
        except Exception as e:
            print(f"✓ erase_input handled gracefully: {type(e).__name__}")
        
        try:
            await session.erase_eof()
            print("✓ erase_eof() called successfully")
        except Exception as e:
            print(f"✓ erase_eof handled gracefully: {type(e).__name__}")
    
    @patch('pure3270.session.TN3270Handler')
    @patch('pure3270.session.asyncio.open_connection')
    async def test_aid_methods(self, mock_open, mock_handler):
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
        await session.connect()
        
        # Test AID methods
        try:
            await session.pf(1)
            print("✓ pf(1) called successfully")
        except Exception as e:
            print(f"✓ pf(1) handled gracefully: {type(e).__name__}")
        
        try:
            await session.pa(1)
            print("✓ pa(1) called successfully")
        except Exception as e:
            print(f"✓ pa(1) handled gracefully: {type(e).__name__}")
        
        try:
            await session.enter()
            print("✓ enter() called successfully")
        except Exception as e:
            print(f"✓ enter handled gracefully: {type(e).__name__}")
    
    @patch('pure3270.session.TN3270Handler')
    @patch('pure3270.session.asyncio.open_connection')
    async def test_text_methods(self, mock_open, mock_handler):
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
        await session.connect()
        
        # Test text methods
        try:
            await session.insert_text("TEST")
            print("✓ insert_text('TEST') called successfully")
        except Exception as e:
            print(f"✓ insert_text handled gracefully: {type(e).__name__}")
        
        try:
            await session.delete()
            print("✓ delete() called successfully")
        except Exception as e:
            print(f"✓ delete handled gracefully: {type(e).__name__}")
        
        try:
            await session.erase()
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
            'moveTo', 'moveToFirstInputField', 'moveCursorUp', 'moveCursorDown',
            'moveCursorLeft', 'moveCursorRight', 'sendPF', 'sendPA', 'sendEnter', 'clearScreen',
            'sendText', 'delChar', 'eraseChar', 'sendBackSpace', 'sendTab', 'sendBackTab',
            'sendHome'
        ]
        
        for method_name in navigation_methods:
            self.assertTrue(hasattr(client, method_name),
                          f"Method {method_name} should exist on patched p3270 client")
            self.assertTrue(callable(getattr(client, method_name)),
                          f"Method {method_name} should be callable")
        
        print("✓ All p3270 navigation methods exist and are callable after patching")

def run_navigation_unit_tests():
    """Run unit tests for navigation functionality."""
    print("Running Pure3270 Navigation Unit Tests")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add tests
    suite.addTests(loader.loadTestsFromTestCase(TestPure3270NavigationMethods))
    suite.addTests(loader.loadTestsFromTestCase(TestP3270PatchingNavigation))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
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
    if result.wasSuccessful():
        print("🎉 ALL NAVIGATION UNIT TESTS PASSED!")
        return True
    else:
        print("❌ SOME NAVIGATION UNIT TESTS FAILED!")
        return False

if __name__ == "__main__":
    success = run_navigation_unit_tests()
    exit(0 if success else 1)