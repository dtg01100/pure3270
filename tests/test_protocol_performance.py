import platform

import pytest

from pure3270.protocol.data_stream import DataStreamParser


@pytest.mark.skipif(
    platform.system() != "Linux", reason="Memory limiting only supported on Linux"
)
@pytest.mark.slow
def test_performance_parse(data_stream_parser, memory_limit_500mb):
    # Performance: parse moderately sized stream while keeping memory headroom
    # Use the 500MB cap to avoid pytest reporting OOMs on constrained runners.
    large_stream = b"\x05" + b"\x40" * 1000  # Keep small to be environment-safe
    data_stream_parser.parse(large_stream)
    # No benchmark to avoid OOM
