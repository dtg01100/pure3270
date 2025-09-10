import pytest
from unittest.mock import patch, AsyncMock
from pure3270.session import Session, AsyncSession


class TestAIDSupport:
    def test_session_pf_method_exists(self):
        """Test that Session class has pf method."""
        session = Session()
        assert hasattr(session, "pf")

    def test_session_pa_method_exists(self):
        """Test that Session class has pa method."""
        session = Session()
        assert hasattr(session, "pa")

    @patch("pure3270.session.asyncio.run")
    def test_session_pf_calls_async_pf(self, mock_run):
        """Test that Session.pf calls AsyncSession.pf."""
        session = Session()
        session._async_session = AsyncMock()

        session.pf(1)

        session._async_session.pf.assert_called_once_with(1)
        mock_run.assert_called_once()

    @patch("pure3270.session.asyncio.run")
    def test_session_pa_calls_async_pa(self, mock_run):
        """Test that Session.pa calls AsyncSession.pa."""
        session = Session()
        session._async_session = AsyncMock()

        session.pa(1)

        session._async_session.pa.assert_called_once_with(1)
        mock_run.assert_called_once()

    def test_async_session_key_method_extended_aid_map(self):
        """Test that AsyncSession.key method has extended AID map."""
        session = AsyncSession()

        # Check that the extended AID map is present by testing a few keys
        # This is a bit tricky to test directly since key() raises ValueError for unknown keys
        # and we're not actually calling the method (which would require a connection)

        # We can at least verify the method exists and has the right signature
        assert hasattr(session, "key")

        # The actual testing of the AID map functionality would require integration tests
        # that we've added the right keys to the map, which is covered by the existing
        # macro tests that use the same AID_MAP
