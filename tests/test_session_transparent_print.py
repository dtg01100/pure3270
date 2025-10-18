import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pure3270.session import AsyncSession


@pytest.mark.asyncio
async def test_transparent_printing_integration():
    """Verify that AsyncSession correctly uses the DataFlowController when enabled."""
    # 1. Arrange
    # Patch the DataFlowController and the connect logic.
    with (
        patch(
            "pure3270.session.DataFlowController", autospec=True
        ) as MockDataFlowController,
        patch(
            "pure3270.session.AsyncSession._perform_connect", new_callable=AsyncMock
        ) as mock_connect,
    ):

        # Instantiate the session with transparent printing enabled.
        session = AsyncSession(
            host="localhost",
            transparent_print_host="printer.example.com",
        )

        # Get the instance of the mocked controller that was created in __init__
        controller_instance = MockDataFlowController.return_value
        controller_instance.process_main_session_data = AsyncMock(
            return_value=(b"main_data", None)
        )

        # 2. Act
        # Call connect, which will use the mocked _perform_connect.
        await session.connect()

        # Manually set state that _perform_connect would have set.
        session.connected = True
        session._handler = AsyncMock()
        dummy_data = b"some_data_stream"
        session._handler.receive_data = AsyncMock(return_value=dummy_data)

        response_data = await session.read()

        # 3. Assert
        # Verify that the DataFlowController was started.
        controller_instance.start.assert_called_once()

        # Verify that process_main_session_data was called with the dummy data.
        controller_instance.process_main_session_data.assert_awaited_once_with(
            dummy_data,
            None,  # Header
            str(id(session)),
            "printer.example.com",
            23,
        )

        # Verify that the data returned from read() is the data from the controller.
        assert response_data == b"main_data"

        # Verify the controller is stopped on close.
        await session.close()
        controller_instance.stop.assert_called_once()
