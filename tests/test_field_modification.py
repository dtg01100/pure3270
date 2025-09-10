import pytest
from pure3270.emulation.screen_buffer import ScreenBuffer, Field


class TestFieldModificationTracking:
    def test_field_modification_with_write_char_fixed_behavior(self):
        """Test that writing to a field updates its modified flag."""
        # Create a screen buffer
        screen = ScreenBuffer(rows=2, cols=20)

        # Set up a simple field manually for testing
        # Field from position (0, 5) to (0, 10)
        field = Field(
            (0, 5), (0, 10), protected=False, content=b"\x40\x40\x40\x40\x40\x40"
        )  # 6 spaces
        screen.fields = [field]

        # Initially, the field should not be marked as modified
        assert field.modified is False

        # Write a character to the field position
        screen.write_char(0xC1, 0, 5)  # Write 'A' at position (0, 5)

        # With our fix, the field's modified flag should now be set to True
        assert field.modified is True  # This should now pass

        # The field's content is still not updated in this simple implementation
        # but the modified flag is properly set

    def test_field_modification_with_set_content(self):
        """Test that set_content properly marks field as modified."""
        # Create a field
        field = Field(
            (0, 0), (0, 5), protected=False, content=b"\x40\x40\x40\x40\x40\x40"
        )

        # Initially, the field should not be marked as modified
        assert field.modified is False

        # Set content using set_content method
        field.set_content("Hello!")

        # The field's modified flag should be set to True
        assert field.modified is True

        # The field's content should be updated
        assert field.get_content() == "Hello!"

    def test_read_modified_fields_basic(self):
        """Test basic read_modified_fields functionality."""
        screen = ScreenBuffer(rows=2, cols=20)

        # Set up fields
        field1 = Field(
            (0, 0),
            (0, 5),
            protected=False,
            content=b"\x40\x40\x40\x40\x40\x40",
            modified=False,
        )
        field2 = Field(
            (0, 10),
            (0, 15),
            protected=False,
            content=b"\x40\x40\x40\x40\x40\x40",
            modified=True,
        )
        screen.fields = [field1, field2]

        # Read modified fields
        modified = screen.read_modified_fields()

        # Only field2 should be returned since it's marked as modified
        assert len(modified) == 1
        assert modified[0][0] == (0, 10)  # Start position of field2
        assert modified[0][1] == "      "  # Content of field2 (6 spaces)
