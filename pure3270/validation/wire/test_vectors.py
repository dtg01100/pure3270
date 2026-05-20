"""Pytest adapter for wire-level test vectors."""

import pytest

from pure3270.validation.wire.runner import WireVector, load_vectors, run_vector

VECTORS = load_vectors()


@pytest.mark.parametrize(
    "vector",
    [pytest.param(v, id=v.id) for v in VECTORS],
)
@pytest.mark.asyncio
async def test_wire_vector(vector: WireVector) -> None:
    """Run a single wire vector test."""
    result = await run_vector(vector)
    if not result["passed"]:
        pytest.fail(result.get("error", "Unknown failure"))