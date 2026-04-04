import platform
from unittest.mock import AsyncMock, Mock, patch

import pytest

from pure3270.session import AsyncSession, Session


@pytest.mark.skipif(
    platform.system() != "Linux", reason="Memory limiting only supported on Linux"
)
class TestAIDSupport:
    def test_session_pf_method_exists(self, memory_limit_500mb):
        """Test that Session class has pf method and it's callable."""
        session = Session()
        assert hasattr(session, "pf")
        assert callable(session.pf)

    def test_session_pa_method_exists(self, memory_limit_500mb):
        """Test that Session class has pa method and it's callable."""
        session = Session()
        assert hasattr(session, "pa")
        assert callable(session.pa)

    def test_session_pf_calls_async_pf(self, memory_limit_500mb):
        """Test that Session.pf calls AsyncSession.pf."""
        session = Session()
        session._async_session = AsyncMock()
        # Mock _run_async to avoid thread synchronization issues
        session._run_async = Mock(side_effect=lambda coro: coro.close())

        session.pf(1)

        session._async_session.pf.assert_called_once_with(1)

    def test_session_pa_calls_async_pa(self, memory_limit_500mb):
        """Test that Session.pa calls AsyncSession.pa."""
        session = Session()
        session._async_session = AsyncMock()
        # Mock _run_async to avoid thread synchronization issues
        session._run_async = Mock(side_effect=lambda coro: coro.close())

        session.pa(1)

        session._async_session.pa.assert_called_once_with(1)

    def test_async_session_key_method_extended_aid_map(self, memory_limit_500mb):
        """Test that AsyncSession.key method has extended AID map."""
        assert hasattr(AsyncSession, "AID_MAP")
        aid_map = AsyncSession.AID_MAP

        assert "PF(1)" in aid_map
        assert "PF(12)" in aid_map
        assert "PA(1)" in aid_map
        assert "PA(3)" in aid_map
        assert "CLEAR" in aid_map
        assert "Enter" in aid_map
        assert aid_map["PF(1)"] == 0xF1
        assert aid_map["PF(12)"] == 0x7C
