"""Runner for end-to-end acceptance scenarios."""

import asyncio
import logging
from typing import Any, Optional

from pure3270.validation.acceptance.scenarios import Scenario, StepKind

logger = logging.getLogger(__name__)


class ScenarioRunner:
    """Executes a scenario against a mock server."""

    def __init__(self, target: str = "mock"):
        self.target = target
        self._mock_server: Any = None
        self._server_port: Optional[int] = None
        self._async_session: Optional[Any] = None
        self._last_screen: Optional[str] = None

    async def _start_mock_server(self, step: StepKind.StartServer) -> None:
        from mock_server.tn3270_mock_server import EnhancedTN3270MockServer

        self._mock_server = EnhancedTN3270MockServer(host="127.0.0.1", port=0)
        await self._mock_server._start_in_loop()
        self._server_port = self._mock_server.port
        await asyncio.sleep(0.05)

    def _resolve_port(self, port: Any) -> int:
        if port == "$server_port":
            assert self._server_port is not None
            return self._server_port
        return int(port)

    async def _run_connect(self, step: StepKind.Connect) -> None:
        from pure3270.session import AsyncSession

        port = self._resolve_port(step.port)
        self._async_session = AsyncSession()
        await self._async_session.connect(host=step.host, port=port)

    async def _run_send_key(self, step: StepKind.SendKey) -> None:
        assert self._async_session is not None
        await self._async_session.key(step.key)

    async def _run_send_data(self, step: StepKind.SendData) -> None:
        assert self._async_session is not None
        await self._async_session.send(step.data)

    async def _run_receive_data(self, step: StepKind.ReceiveData) -> str:
        assert self._async_session is not None
        data = await self._async_session.read(timeout=step.timeout)
        if data:
            self._last_screen = str(data)
        return self._last_screen or ""

    async def _run_assert_state(self, step: StepKind.AssertState) -> None:
        assert self._async_session is not None
        handler = self._async_session._handler
        state_name = handler._current_state if handler else None
        if state_name != step.state:
            raise AssertionError(f"Expected state {step.state}, got {state_name}")

    async def _run_assert_screen_contains(
        self, step: StepKind.AssertScreenContains
    ) -> None:
        assert self._async_session is not None
        screen = self._async_session._screen_buffer
        if screen is None:
            raise AssertionError("No screen buffer available")
        text = screen.get_text() if hasattr(screen, "get_text") else str(screen)
        if step.text not in text:
            raise AssertionError(
                f"Screen does not contain '{step.text}'. Screen: {text[:200]}"
            )

    async def _run_assert_screen_updated(
        self, step: StepKind.AssertScreenUpdated
    ) -> None:
        pass

    async def _run_disconnect(self, step: StepKind.Disconnect) -> None:
        if self._async_session is not None:
            await self._async_session.close()

    async def run_scenario(self, scenario: Scenario) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": scenario.name,
            "passed": True,
            "steps_passed": 0,
            "steps_total": len(scenario.steps),
            "error": None,
        }

        try:
            for step in scenario.steps:
                if isinstance(step, StepKind.StartServer):
                    await self._start_mock_server(step)
                elif isinstance(step, StepKind.Connect):
                    await self._run_connect(step)
                elif isinstance(step, StepKind.SendKey):
                    await self._run_send_key(step)
                elif isinstance(step, StepKind.SendData):
                    await self._run_send_data(step)
                elif isinstance(step, StepKind.ReceiveData):
                    await self._run_receive_data(step)
                elif isinstance(step, StepKind.AssertState):
                    await self._run_assert_state(step)
                elif isinstance(step, StepKind.AssertScreenContains):
                    await self._run_assert_screen_contains(step)
                elif isinstance(step, StepKind.AssertScreenUpdated):
                    await self._run_assert_screen_updated(step)
                elif isinstance(step, StepKind.Wait):
                    await asyncio.sleep(step.seconds)
                elif isinstance(step, StepKind.Disconnect):
                    await self._run_disconnect(step)

                result["steps_passed"] += 1

        except Exception as e:
            result["passed"] = False
            result["error"] = (
                f"Step {result['steps_passed']}/{result['steps_total']}: {type(e).__name__}: {e}"
            )
            logger.exception(
                f"Scenario '{scenario.name}' failed at step {result['steps_passed']}"
            )

        finally:
            if self._async_session is not None:
                try:
                    await self._async_session.close()
                except Exception:
                    pass
            if self._mock_server is not None:
                try:
                    self._mock_server._server.close()
                except Exception:
                    pass

        return result
