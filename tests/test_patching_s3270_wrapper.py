#!/usr/bin/env python3
"""
Tests for the s3270 wrapper functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import logging

# Set up logging for tests
logging.basicConfig(level=logging.DEBUG)


class TestPure3270S3270Wrapper:
    """Tests for Pure3270S3270Wrapper class."""

    @pytest.fixture
    def wrapper(self):
        """Create a wrapper instance for testing."""
        from pure3270.patching.s3270_wrapper import Pure3270S3270Wrapper

        return Pure3270S3270Wrapper(["s3270"])

    def test_init(self, wrapper):
        """Test initialization."""
        assert wrapper.args == ["s3270"]
        assert wrapper.encoding == "latin1"
        assert wrapper.buffer is None
        assert wrapper.statusMsg is None
        assert hasattr(wrapper, "_session")

    def test_do_command_success(self, wrapper):
        """Test successful command execution."""
        with patch.object(wrapper, "_execute_command", return_value=True):
            result = wrapper.do("Enter")
            assert result is True

    def test_do_command_failure(self, wrapper):
        """Test failed command execution."""
        with patch.object(
            wrapper, "_execute_command", side_effect=Exception("Test error")
        ):
            result = wrapper.do("Enter")
            assert result is False
            assert wrapper.statusMsg is not None

    def test_execute_command_connect(self, wrapper):
        """Test Connect command execution."""
        with patch.object(wrapper, "_handle_connect", return_value=True) as mock_handle:
            result = wrapper._execute_command("Connect(B:hostname)")
            assert result is True
            mock_handle.assert_called_once()

    def test_execute_command_disconnect(self, wrapper):
        """Test Disconnect command execution."""
        with patch.object(
            wrapper, "_handle_disconnect", return_value=True
        ) as mock_handle:
            result = wrapper._execute_command("Disconnect")
            assert result is True
            mock_handle.assert_called_once()

    def test_execute_command_enter(self, wrapper):
        """Test Enter command execution."""
        with patch.object(wrapper, "_handle_enter", return_value=True) as mock_handle:
            result = wrapper._execute_command("Enter")
            assert result is True
            mock_handle.assert_called_once()

    def test_execute_command_pf(self, wrapper):
        """Test PF command execution."""
        with patch.object(wrapper, "_handle_pf", return_value=True) as mock_handle:
            result = wrapper._execute_command("PF(1)")
            assert result is True
            mock_handle.assert_called_once_with("PF(1)")

    def test_execute_command_pa(self, wrapper):
        """Test PA command execution."""
        with patch.object(wrapper, "_handle_pa", return_value=True) as mock_handle:
            result = wrapper._execute_command("PA(1)")
            assert result is True
            mock_handle.assert_called_once_with("PA(1)")

    def test_execute_command_string(self, wrapper):
        """Test String command execution."""
        with patch.object(wrapper, "_handle_string", return_value=True) as mock_handle:
            result = wrapper._execute_command("String(test)")
            assert result is True
            mock_handle.assert_called_once_with("String(test)")

    def test_execute_command_clear(self, wrapper):
        """Test Clear command execution."""
        with patch.object(wrapper, "_handle_clear", return_value=True) as mock_handle:
            result = wrapper._execute_command("Clear")
            assert result is True
            mock_handle.assert_called_once()

    def test_execute_command_home(self, wrapper):
        """Test Home command execution."""
        with patch.object(wrapper, "_handle_home", return_value=True) as mock_handle:
            result = wrapper._execute_command("Home")
            assert result is True
            mock_handle.assert_called_once()

    def test_execute_command_unknown(self, wrapper):
        """Test unknown command execution."""
        result = wrapper._execute_command("UnknownCommand")
        assert result is True  # Should return True for compatibility

    def test_handle_connect(self, wrapper):
        """Test Connect command handling."""
        result = wrapper._handle_connect("Connect(B:hostname)")
        assert result is True
        assert wrapper.statusMsg is not None

    def test_handle_disconnect(self, wrapper):
        """Test Disconnect command handling."""
        result = wrapper._handle_disconnect()
        assert result is True
        assert wrapper.statusMsg is not None

    def test_handle_enter_success(self, wrapper):
        """Test successful Enter command handling."""
        with patch.object(wrapper._session, "enter") as mock_enter:
            result = wrapper._handle_enter()
            assert result is True
            mock_enter.assert_called_once()
            assert wrapper.statusMsg is not None

    def test_handle_enter_failure(self, wrapper):
        """Test failed Enter command handling."""
        with patch.object(
            wrapper._session, "enter", side_effect=Exception("Test error")
        ):
            result = wrapper._handle_enter()
            assert result is False
            assert wrapper.statusMsg is not None

    def test_handle_pf_success(self, wrapper):
        """Test successful PF command handling."""
        with patch.object(wrapper._session, "pf") as mock_pf:
            result = wrapper._handle_pf("PF(1)")
            assert result is True
            mock_pf.assert_called_once_with(1)
            assert wrapper.statusMsg is not None

    def test_handle_pf_failure(self, wrapper):
        """Test failed PF command handling."""
        with patch.object(wrapper._session, "pf", side_effect=Exception("Test error")):
            result = wrapper._handle_pf("PF(1)")
            assert result is False
            assert wrapper.statusMsg is not None

    def test_handle_pa_success(self, wrapper):
        """Test successful PA command handling."""
        with patch.object(wrapper._session, "pa") as mock_pa:
            result = wrapper._handle_pa("PA(1)")
            assert result is True
            mock_pa.assert_called_once_with(1)
            assert wrapper.statusMsg is not None

    def test_handle_pa_failure(self, wrapper):
        """Test failed PA command handling."""
        with patch.object(wrapper._session, "pa", side_effect=Exception("Test error")):
            result = wrapper._handle_pa("PA(1)")
            assert result is False
            assert wrapper.statusMsg is not None

    def test_handle_string_success(self, wrapper):
        """Test successful String command handling."""
        # Test that compose is called with the extracted text
        with patch.object(wrapper._session, "compose") as mock_compose:
            result = wrapper._handle_string("String(test)")
            assert result is True
            mock_compose.assert_called_once_with("test")
            assert wrapper.statusMsg is not None

    def test_handle_string_failure(self, wrapper):
        """Test failed String command handling."""
        with patch.object(
            wrapper._session, "compose", side_effect=Exception("Test error")
        ):
            result = wrapper._handle_string("String(test)")
            assert result is False
            assert wrapper.statusMsg is not None

    def test_handle_clear(self, wrapper):
        """Test Clear command handling."""
        with patch.object(wrapper._session, "erase") as mock_erase:
            result = wrapper._handle_clear()
            assert result is True
            mock_erase.assert_called_once()
            assert wrapper.statusMsg is not None

    def test_handle_home_success(self, wrapper):
        """Test successful Home command handling."""
        with patch.object(wrapper._session, "home") as mock_home:
            result = wrapper._handle_home()
            assert result is True
            mock_home.assert_called_once()
            assert wrapper.statusMsg is not None

    def test_handle_home_failure(self, wrapper):
        """Test failed Home command handling."""
        with patch.object(
            wrapper._session, "home", side_effect=Exception("Test error")
        ):
            result = wrapper._handle_home()
            assert result is False
            assert wrapper.statusMsg is not None

    def test_handle_backspace_success(self, wrapper):
        """Test successful BackSpace command handling."""
        with patch.object(wrapper._session, "backspace") as mock_backspace:
            result = wrapper._handle_backspace()
            assert result is True
            mock_backspace.assert_called_once()
            assert wrapper.statusMsg is not None

    def test_handle_backspace_failure(self, wrapper):
        """Test failed BackSpace command handling."""
        with patch.object(
            wrapper._session, "backspace", side_effect=Exception("Test error")
        ):
            result = wrapper._handle_backspace()
            assert result is False
            assert wrapper.statusMsg is not None

    def test_create_status(self, wrapper):
        """Test status message creation."""
        status = wrapper._create_status()
        assert isinstance(status, str)
        assert len(status.split(" ")) == 12  # Should have 12 fields

    def test_create_error_status(self, wrapper):
        """Test error status message creation."""
        status = wrapper._create_error_status()
        assert isinstance(status, str)
        assert "E" in status  # Should indicate error state

    def test_check(self, wrapper):
        """Test check method."""
        result = wrapper.check()
        assert result is True

        result = wrapper.check(doNotCheck=True)
        assert result is True

    def test_instance_counting(self):
        """Test that instance counting works."""
        from pure3270.patching.s3270_wrapper import Pure3270S3270Wrapper

        # Store initial count
        initial_count = Pure3270S3270Wrapper.numOfInstances

        # Create instances
        wrapper1 = Pure3270S3270Wrapper(["s3270"])
        assert Pure3270S3270Wrapper.numOfInstances == initial_count + 1

        wrapper2 = Pure3270S3270Wrapper(["s3270"])
        assert Pure3270S3270Wrapper.numOfInstances == initial_count + 2


if __name__ == "__main__":
    pytest.main([__file__])
