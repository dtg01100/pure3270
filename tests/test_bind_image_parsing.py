import pytest

from pure3270.protocol.data_stream import (
    BIND_OFF_SSIZE,
    BIND_RU,
    MODEL_2_COLS,
    MODEL_2_ROWS,
    DataStreamParser,
)


def test_parse_bind_image_model2_defaults():
    # Create a minimal BIND RU buffer where the screen size byte indicates model 2
    buf = bytearray(40)
    buf[0] = BIND_RU
    # Set the screen size offset to 0x00 (model 2 default)
    buf[BIND_OFF_SSIZE] = 0x00

    parser = DataStreamParser(None)
    bind_image = parser._parse_bind_image(bytes(buf))

    assert bind_image.rows == MODEL_2_ROWS
    assert bind_image.cols == MODEL_2_COLS


def test_parse_bind_image_invalid_start_returns_empty_bind_image():
    # Buffer that does not start with BIND_RU should return empty BindImage
    buf = bytearray(10)
    buf[0] = 0x00  # not BIND_RU
    parser = DataStreamParser(None)
    bind_image = parser._parse_bind_image(bytes(buf))

    # When invalid, BindImage should have None dimensions
    assert bind_image.rows is None
    assert bind_image.cols is None
