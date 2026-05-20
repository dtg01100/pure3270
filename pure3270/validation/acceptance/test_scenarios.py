"""Pytest adapter for acceptance scenarios."""

import pytest

from pure3270.validation.acceptance.runner import ScenarioRunner
from pure3270.validation.acceptance.scenarios import Scenario, create_default_scenarios

SCENARIOS = create_default_scenarios()


@pytest.mark.acceptance
@pytest.mark.parametrize(
    "scenario",
    [pytest.param(s, id=s.name) for s in SCENARIOS],
)
@pytest.mark.asyncio
async def test_acceptance_scenario(scenario: Scenario) -> None:
    runner = ScenarioRunner(target="mock")
    result = await runner.run_scenario(scenario)
    if not result["passed"]:
        pytest.fail(result.get("error", "Scenario failed"))
