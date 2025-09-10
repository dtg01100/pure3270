import pytest
from pure3270.emulation.screen_buffer import ScreenBuffer, Field


class TestExtendedFieldAttributes:
    def test_field_extended_attributes(self):
        """Test that Field class supports extended attributes."""
        # Create a field with extended attributes
        field = Field(
            start=(0, 0),
            end=(0, 10),
            protected=False,
            numeric=False,
            modified=False,
            selected=False,
            intensity=1,  # Highlighted
            color=2,  # Red
            background=3,  # Pink
            validation=1,  # Mandatory fill
            outlining=1,  # Underscore
            content=b"\x40" * 11,  # 11 spaces
        )

        # Basic attributes
        assert field.protected is False
        assert field.numeric is False
        assert field.modified is False
        assert field.selected is False
        assert field.content == b"\x40" * 11

        # Extended attributes
        assert field.intensity == 1
        assert field.color == 2
        assert field.background == 3
        assert field.validation == 1
        assert field.outlining == 1

    def test_field_default_attributes(self):
        """Test that Field class has sensible defaults for extended attributes."""
        field = Field(start=(0, 0), end=(0, 10), content=b"\x40" * 11)

        # Basic attributes should have sensible defaults
        assert field.protected is False
        assert field.numeric is False
        assert field.modified is False
        assert field.selected is False

        # Extended attributes should have sensible defaults
        assert field.intensity == 0  # Normal intensity
        assert field.color == 0  # Default color
        assert field.background == 0  # Default background
        assert field.validation == 0  # No validation
        assert field.outlining == 0  # No outlining

    def test_screen_buffer_extended_attribute_storage(self):
        """Test that screen buffer properly stores extended attributes."""
        screen = ScreenBuffer(rows=2, cols=20)

        # The attributes buffer should support storing extended attributes
        # Currently it has 3 bytes per position:
        # Byte 0: Protection and other basic attributes
        # Byte 1: Intensity or foreground color
        # Byte 2: Validation or background/highlight
        assert len(screen.attributes) == screen.size * 3

    def test_field_repr_includes_extended_attributes(self):
        """Test that Field repr includes some extended attributes."""
        field = Field(
            start=(0, 0),
            end=(0, 10),
            protected=False,
            intensity=1,
            content=b"\x40" * 11,
        )

        # The repr should include at least some key attributes
        repr_str = repr(field)
        assert "start=(0, 0)" in repr_str
        assert "end=(0, 10)" in repr_str
        assert "protected=False" in repr_str
        assert "intensity=1" in repr_str
