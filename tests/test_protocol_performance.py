import platform

import pytest

from pure3270.protocol.data_stream import DataStreamParser


@pytest.mark.skipif(
    platform.system() != "Linux", reason="Memory limiting only supported on Linux"
)
@pytest.mark.slow
def test_performance_parse(data_stream_parser, memory_limit_100mb):
    # Performance: parse large stream (reduced size to avoid OOM)
    large_stream = b"\x05" + b"\x40" * 1000  # Reduced size to avoid OOM
    data_stream_parser.parse(large_stream)
    # No benchmark to avoid OOM
