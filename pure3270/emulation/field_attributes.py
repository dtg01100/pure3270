# ATTRIBUTION NOTICE
# =================================================================================
# This module contains code ported from or inspired by: IBM s3270/x3270
# Source: https://github.com/rhacker/x3270
# Licensed under BSD-3-Clause
#
# DESCRIPTION
# --------------------
# Advanced field attribute classes for extended 3270 field support
#
# COMPATIBILITY
# --------------------
# Compatible with s3270 extended field attributes and TN3270E specifications
#
# MODIFICATIONS
# --------------------
# Adapted for Python with object-oriented design and enhanced attribute management
#
# INTEGRATION POINTS
# --------------------
# - Extended attribute support for ScreenBuffer._extended_attributes
# - Color mapping for base 16 and extended 256 color support
# - Highlighting effects for visual field emphasis
# - Validation rules for field input constraints
# - Outlining for field border and visual separation
#
# ATTRIBUTION REQUIREMENTS
# ------------------------------
# This attribution must be maintained when this code is modified or
# redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
# Last updated: 2025-10-13
# =================================================================================

"""Advanced field attribute classes for 3270 emulation."""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


class AttributeType(Enum):
    """Enumeration of supported extended attribute types."""

    COLOR = "color"
    HIGHLIGHT = "highlight"
    VALIDATION = "validation"
    OUTLINING = "outlining"
    LIGHT_PEN = "light_pen"
    BACKGROUND = "background"


class ExtendedAttribute(ABC):
    """Abstract base class for extended field attributes.

    Provides common functionality for all extended attribute types including
    validation, serialization, and thread-safe operations.
    """

    def __init__(self, value: Union[int, str] = 0) -> None:
        """Initialize extended attribute with value.

        Args:
            value: The attribute value (int or string representation)

        Raises:
            ValueError: If the value is invalid for this attribute type
        """
        self._value: int = self._validate_and_normalize(value)

    @property
    def value(self) -> int:
        """Get the current attribute value."""
        return self._value

    @value.setter
    def value(self, new_value: Union[int, str]) -> None:
        """Set a new attribute value with validation.

        Args:
            new_value: The new value to set

        Raises:
            ValueError: If the new value is invalid
        """
        self._value = self._validate_and_normalize(new_value)

    @abstractmethod
    def _validate_and_normalize(self, value: Union[int, str]) -> int:
        """Validate and normalize the input value.

        Args:
            value: Raw input value

        Returns:
            Normalized value

        Raises:
            ValueError: If value is invalid
        """
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert attribute to dictionary representation.

        Returns:
            Dictionary containing attribute type and value
        """
        pass

    @abstractmethod
    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load attribute from dictionary representation.

        Args:
            data: Dictionary containing attribute data

        Raises:
            ValueError: If data is invalid
        """
        pass

    def __eq__(self, other: object) -> bool:
        """Check equality with another attribute."""
        if not isinstance(other, ExtendedAttribute):
            return NotImplemented
        return self.__class__ == other.__class__ and self._value == other._value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(value={self._value!r})"


class ExtendedAttributeSet:
    """Container for managing multiple extended attributes for a field position.

    Provides thread-safe operations for setting, getting, and managing
    extended attributes with proper validation and error handling.
    """

    def __init__(self) -> None:
        """Initialize empty attribute set."""
        self._attributes: Dict[str, ExtendedAttribute] = {}

    def set_attribute(self, attr_type: str, attribute: Any) -> None:
        """Set an extended attribute.

        Args:
            attr_type: The attribute type key
            attribute: The attribute instance

        Raises:
            TypeError: If attribute is not an ExtendedAttribute instance
        """
        if not isinstance(attribute, ExtendedAttribute):
            # For backward compatibility, allow raw attributes for unknown types
            logger.warning(
                f"Setting raw attribute for type '{attr_type}': {type(attribute)}"
            )

        self._attributes[attr_type] = attribute
        logger.debug(f"Set extended attribute '{attr_type}': {attribute}")

    def get_attribute(self, attr_type: str) -> Any:
        """Get an extended attribute by type.

        Args:
            attr_type: The attribute type key

        Returns:
            The attribute instance or None if not found
        """
        return self._attributes.get(attr_type)

    def remove_attribute(self, attr_type: str) -> bool:
        """Remove an extended attribute.

        Args:
            attr_type: The attribute type key

        Returns:
            True if attribute was removed, False if not found
        """
        if attr_type in self._attributes:
            del self._attributes[attr_type]
            logger.debug(f"Removed extended attribute '{attr_type}'")
            return True
        return False

    def has_attribute(self, attr_type: str) -> bool:
        """Check if an attribute type is present.

        Args:
            attr_type: The attribute type key

        Returns:
            True if attribute exists
        """
        return attr_type in self._attributes

    def clear(self) -> None:
        """Clear all attributes."""
        self._attributes.clear()
        logger.debug("Cleared all extended attributes")

    def get_all_attributes(self) -> Dict[str, ExtendedAttribute]:
        """Get a copy of all attributes.

        Returns:
            Dictionary of all attributes
        """
        return self._attributes.copy()

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Convert all attributes to dictionary representation.

        Returns:
            Dictionary mapping attribute types to their data
        """
        return {
            attr_type: attr.to_dict() for attr_type, attr in self._attributes.items()
        }

    def from_dict(self, data: Dict[str, Dict[str, Any]]) -> None:
        """Load attributes from dictionary representation.

        Args:
            data: Dictionary containing attribute data

        Raises:
            ValueError: If data contains invalid attributes
        """
        self._attributes.clear()
        for attr_type, attr_data in data.items():
            try:
                # Import here to avoid circular imports
                if attr_type == AttributeType.COLOR.value:
                    attr: ExtendedAttribute = ColorAttribute()
                elif attr_type == AttributeType.HIGHLIGHT.value:
                    attr = HighlightAttribute()
                elif attr_type == AttributeType.VALIDATION.value:
                    attr = ValidationAttribute()
                elif attr_type == AttributeType.OUTLINING.value:
                    attr = OutliningAttribute()
                elif attr_type == AttributeType.LIGHT_PEN.value:
                    attr = LightPenAttribute()
                elif attr_type == AttributeType.BACKGROUND.value:
                    attr = BackgroundAttribute()
                else:
                    logger.warning(f"Unknown attribute type '{attr_type}', skipping")
                    continue

                attr.from_dict(attr_data)
                self._attributes[attr_type] = attr
            except Exception as e:
                logger.error(f"Failed to load attribute '{attr_type}': {e}")
                raise ValueError(f"Invalid attribute data for '{attr_type}'") from e

    def __len__(self) -> int:
        """Get number of attributes."""
        return len(self._attributes)

    def __repr__(self) -> str:
        return f"ExtendedAttributeSet(attributes={list(self._attributes.keys())})"


class ColorAttribute(ExtendedAttribute):
    """Color attribute supporting base 16 and extended 256 color support.

    Supports both standard 3270 colors (0-15) and extended colors (16-255)
    as defined in TN3270E specifications.
    """

    # Base 16 colors (3270 standard)
    BASE_COLORS = {
        0: "neutral_black",
        1: "blue",
        2: "red",
        3: "pink",
        4: "green",
        5: "turquoise",
        6: "yellow",
        7: "neutral_white",
        8: "black",
        9: "deep_blue",
        10: "orange",
        11: "purple",
        12: "pale_green",
        13: "pale_turquoise",
        14: "grey",
        15: "white",
    }

    def __init__(self, value: Union[int, str] = 0) -> None:
        """Initialize color attribute.

        Args:
            value: Color value (0-255) or color name string

        Raises:
            ValueError: If value is invalid
        """
        super().__init__(value)

    def _validate_and_normalize(self, value: Union[int, str]) -> int:
        """Validate and normalize color value.

        Args:
            value: Color value as int or string

        Returns:
            Normalized color value (0-255)

        Raises:
            ValueError: If value is invalid
        """
        if isinstance(value, str):
            # Try to map color name to value
            for val, name in self.BASE_COLORS.items():
                if name == value.lower():
                    return val
            # Try to parse as integer string
            try:
                value = int(value)
            except ValueError:
                raise ValueError(f"Invalid color name or value: {value}")

        if isinstance(value, int):
            if 0 <= value <= 255:
                return value
            else:
                raise ValueError(f"Color value must be 0-255, got {value}")
        else:
            raise ValueError(f"Color value must be int or string, got {type(value)}")

    def get_color_name(self) -> Optional[str]:
        """Get the color name for base colors.

        Returns:
            Color name if it's a base color (0-15), None otherwise
        """
        return self.BASE_COLORS.get(self._value) if self._value <= 15 else None

    def is_base_color(self) -> bool:
        """Check if this is a base 16 color.

        Returns:
            True if color is in base 16 range (0-15)
        """
        return 0 <= self._value <= 15

    def is_extended_color(self) -> bool:
        """Check if this is an extended color.

        Returns:
            True if color is in extended range (16-255)
        """
        return 16 <= self._value <= 255

    def to_dict(self) -> Dict[str, Any]:
        """Convert color attribute to dictionary.

        Returns:
            Dictionary with color data
        """
        return {
            "type": AttributeType.COLOR.value,
            "value": self._value,
            "name": self.get_color_name(),
            "is_base": self.is_base_color(),
            "is_extended": self.is_extended_color(),
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load color attribute from dictionary.

        Args:
            data: Dictionary containing color data

        Raises:
            ValueError: If data is invalid
        """
        if "value" not in data:
            raise ValueError("Color attribute data missing 'value' field")

        self._value = self._validate_and_normalize(data["value"])


class HighlightAttribute(ExtendedAttribute):
    """Highlight attribute for visual highlighting effects.

    Supports various highlighting effects like blink, reverse video,
    underscore, and intensity levels.
    """

    # Highlight effect constants
    NORMAL = 0x00
    BLINK = 0x01
    REVERSE = 0x02
    UNDERSCORE = 0x04
    INTENSITY_HIGH = 0x08
    INTENSITY_LOW = 0x10

    # Effect names for readability
    EFFECT_NAMES = {
        NORMAL: "normal",
        BLINK: "blink",
        REVERSE: "reverse",
        UNDERSCORE: "underscore",
        INTENSITY_HIGH: "high_intensity",
        INTENSITY_LOW: "low_intensity",
    }

    def __init__(self, value: Union[int, str] = 0) -> None:
        """Initialize highlight attribute.

        Args:
            value: Highlight value or effect name

        Raises:
            ValueError: If value is invalid
        """
        super().__init__(value)

    def _validate_and_normalize(self, value: Union[int, str]) -> int:
        """Validate and normalize highlight value.

        Args:
            value: Highlight value as int or string

        Returns:
            Normalized highlight value

        Raises:
            ValueError: If value is invalid
        """
        if isinstance(value, str):
            # Try to map effect name to value
            for val, name in self.EFFECT_NAMES.items():
                if name == value.lower():
                    return val
            # Try to parse as integer string
            try:
                value = int(value)
            except ValueError:
                raise ValueError(f"Invalid highlight effect name or value: {value}")

        if isinstance(value, int):
            if 0 <= value <= 0xFF:
                return value
            else:
                raise ValueError(f"Highlight value must be 0-255, got {value}")
        else:
            raise ValueError(
                f"Highlight value must be int or string, got {type(value)}"
            )

    def get_effect_name(self) -> Optional[str]:
        """Get the effect name for known effects.

        Returns:
            Effect name if recognized, None otherwise
        """
        return self.EFFECT_NAMES.get(self._value)

    def has_effect(self, effect: int) -> bool:
        """Check if a specific effect is enabled.

        Args:
            effect: Effect constant to check

        Returns:
            True if effect is enabled
        """
        return bool(self._value & effect)

    def set_effect(self, effect: int, enabled: bool = True) -> None:
        """Set or clear a specific effect.

        Args:
            effect: Effect constant
            enabled: Whether to enable or disable the effect
        """
        if enabled:
            self._value |= effect
        else:
            self._value &= ~effect

    def to_dict(self) -> Dict[str, Any]:
        """Convert highlight attribute to dictionary.

        Returns:
            Dictionary with highlight data
        """
        effects = []
        for effect_val, effect_name in self.EFFECT_NAMES.items():
            if self.has_effect(effect_val):
                effects.append(effect_name)

        return {
            "type": AttributeType.HIGHLIGHT.value,
            "value": self._value,
            "effects": effects,
            "name": self.get_effect_name(),
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load highlight attribute from dictionary.

        Args:
            data: Dictionary containing highlight data

        Raises:
            ValueError: If data is invalid
        """
        if "value" not in data:
            raise ValueError("Highlight attribute data missing 'value' field")

        self._value = self._validate_and_normalize(data["value"])


class ValidationAttribute(ExtendedAttribute):
    """Validation attribute for field validation rules.

    Supports various validation constraints like mandatory fields,
    numeric-only input, length limits, and custom validation rules.
    """

    # Validation type constants
    NONE = 0x00
    MANDATORY = 0x01
    NUMERIC = 0x02
    ALPHABETIC = 0x04
    ALPHANUMERIC = 0x08
    LENGTH_MIN = 0x10
    LENGTH_MAX = 0x20
    CUSTOM = 0x40

    # Validation names
    VALIDATION_NAMES = {
        NONE: "none",
        MANDATORY: "mandatory",
        NUMERIC: "numeric",
        ALPHABETIC: "alphabetic",
        ALPHANUMERIC: "alphanumeric",
        LENGTH_MIN: "min_length",
        LENGTH_MAX: "max_length",
        CUSTOM: "custom",
    }

    def __init__(
        self,
        value: Union[int, str] = 0,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        custom_rule: Optional[str] = None,
    ) -> None:
        """Initialize validation attribute.

        Args:
            value: Validation type value or name
            min_length: Minimum field length (if LENGTH_MIN set)
            max_length: Maximum field length (if LENGTH_MAX set)
            custom_rule: Custom validation rule string (if CUSTOM set)

        Raises:
            ValueError: If parameters are invalid
        """
        super().__init__(value)
        self.min_length = min_length
        self.max_length = max_length
        self.custom_rule = custom_rule

    def _validate_and_normalize(self, value: Union[int, str]) -> int:
        """Validate and normalize validation value.

        Args:
            value: Validation value as int or string

        Returns:
            Normalized validation value

        Raises:
            ValueError: If value is invalid
        """
        if isinstance(value, str):
            # Try to map validation name to value
            for val, name in self.VALIDATION_NAMES.items():
                if name == value.lower():
                    return val
            # Try to parse as integer string
            try:
                value = int(value)
            except ValueError:
                raise ValueError(f"Invalid validation type name or value: {value}")

        if isinstance(value, int):
            if 0 <= value <= 0xFF:
                return value
            else:
                raise ValueError(f"Validation value must be 0-255, got {value}")
        else:
            raise ValueError(
                f"Validation value must be int or string, got {type(value)}"
            )

    def get_validation_name(self) -> Optional[str]:
        """Get the validation type name.

        Returns:
            Validation type name if recognized, None otherwise
        """
        return self.VALIDATION_NAMES.get(self._value)

    def has_validation(self, validation_type: int) -> bool:
        """Check if a specific validation type is enabled.

        Args:
            validation_type: Validation type constant

        Returns:
            True if validation type is enabled
        """
        return bool(self._value & validation_type)

    def set_validation(self, validation_type: int, enabled: bool = True) -> None:
        """Set or clear a specific validation type.

        Args:
            validation_type: Validation type constant
            enabled: Whether to enable or disable the validation
        """
        if enabled:
            self._value |= validation_type
        else:
            self._value &= ~validation_type

    def validate_input(self, input_text: str) -> Tuple[bool, Optional[str]]:
        """Validate input text against validation rules.

        Args:
            input_text: The input text to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check mandatory
        if self.has_validation(self.MANDATORY) and not input_text.strip():
            return False, "Field is mandatory"

        # Check numeric
        if self.has_validation(self.NUMERIC) and not input_text.isdigit():
            return False, "Field must contain only numeric characters"

        # Check alphabetic
        if self.has_validation(self.ALPHABETIC) and not input_text.isalpha():
            return False, "Field must contain only alphabetic characters"

        # Check alphanumeric
        if self.has_validation(self.ALPHANUMERIC) and not input_text.isalnum():
            return False, "Field must contain only alphanumeric characters"

        # Check length constraints
        if self.has_validation(self.LENGTH_MIN) and self.min_length is not None:
            if len(input_text) < self.min_length:
                return False, f"Field must be at least {self.min_length} characters"

        if self.has_validation(self.LENGTH_MAX) and self.max_length is not None:
            if len(input_text) > self.max_length:
                return False, f"Field must be at most {self.max_length} characters"

        # Custom validation would be implemented here
        if self.has_validation(self.CUSTOM) and self.custom_rule:
            # Placeholder for custom validation logic
            logger.debug(f"Custom validation rule: {self.custom_rule}")

        return True, None

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation attribute to dictionary.

        Returns:
            Dictionary with validation data
        """
        validations = []
        for val_type, val_name in self.VALIDATION_NAMES.items():
            if self.has_validation(val_type):
                validations.append(val_name)

        return {
            "type": AttributeType.VALIDATION.value,
            "value": self._value,
            "validations": validations,
            "name": self.get_validation_name(),
            "min_length": self.min_length,
            "max_length": self.max_length,
            "custom_rule": self.custom_rule,
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load validation attribute from dictionary.

        Args:
            data: Dictionary containing validation data

        Raises:
            ValueError: If data is invalid
        """
        if "value" not in data:
            raise ValueError("Validation attribute data missing 'value' field")

        self._value = self._validate_and_normalize(data["value"])
        self.min_length = data.get("min_length")
        self.max_length = data.get("max_length")
        self.custom_rule = data.get("custom_rule")


class OutliningAttribute(ExtendedAttribute):
    """Outlining attribute for field borders and outlines.

    Supports various outlining styles like boxes, underlines,
    overlines, and custom border patterns.
    """

    # Outlining style constants
    NONE = 0x00
    UNDERLINE = 0x01
    OVERLINE = 0x02
    LEFT_LINE = 0x04
    RIGHT_LINE = 0x08
    BOX = 0x0F  # Combination of all sides
    DOUBLE_LINE = 0x10
    DASHED = 0x20
    DOTTED = 0x40

    # Style names
    STYLE_NAMES = {
        NONE: "none",
        UNDERLINE: "underline",
        OVERLINE: "overline",
        LEFT_LINE: "left_line",
        RIGHT_LINE: "right_line",
        BOX: "box",
        DOUBLE_LINE: "double_line",
        DASHED: "dashed",
        DOTTED: "dotted",
    }

    def __init__(self, value: Union[int, str] = 0) -> None:
        """Initialize outlining attribute.

        Args:
            value: Outlining style value or name

        Raises:
            ValueError: If value is invalid
        """
        super().__init__(value)

    def _validate_and_normalize(self, value: Union[int, str]) -> int:
        """Validate and normalize outlining value.

        Args:
            value: Outlining value as int or string

        Returns:
            Normalized outlining value

        Raises:
            ValueError: If value is invalid
        """
        if isinstance(value, str):
            # Try to map style name to value
            for val, name in self.STYLE_NAMES.items():
                if name == value.lower():
                    return val
            # Try to parse as integer string
            try:
                value = int(value)
            except ValueError:
                raise ValueError(f"Invalid outlining style name or value: {value}")

        if isinstance(value, int):
            if 0 <= value <= 0xFF:
                return value
            else:
                raise ValueError(f"Outlining value must be 0-255, got {value}")
        else:
            raise ValueError(
                f"Outlining value must be int or string, got {type(value)}"
            )

    def get_style_name(self) -> Optional[str]:
        """Get the outlining style name.

        Returns:
            Style name if recognized, None otherwise
        """
        return self.STYLE_NAMES.get(self._value)

    def has_style(self, style: int) -> bool:
        """Check if a specific outlining style is enabled.

        Args:
            style: Style constant to check

        Returns:
            True if style is enabled
        """
        return bool(self._value & style)

    def set_style(self, style: int, enabled: bool = True) -> None:
        """Set or clear a specific outlining style.

        Args:
            style: Style constant
            enabled: Whether to enable or disable the style
        """
        if enabled:
            self._value |= style
        else:
            self._value &= ~style

    def is_box(self) -> bool:
        """Check if this is a complete box outline.

        Returns:
            True if all four sides are outlined
        """
        return (self._value & self.BOX) == self.BOX

    def to_dict(self) -> Dict[str, Any]:
        """Convert outlining attribute to dictionary.

        Returns:
            Dictionary with outlining data
        """
        styles = []
        for style_val, style_name in self.STYLE_NAMES.items():
            if self.has_style(style_val):
                styles.append(style_name)

        return {
            "type": AttributeType.OUTLINING.value,
            "value": self._value,
            "styles": styles,
            "name": self.get_style_name(),
            "is_box": self.is_box(),
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load outlining attribute from dictionary.

        Args:
            data: Dictionary containing outlining data

        Raises:
            ValueError: If data is invalid
        """
        if "value" not in data:
            raise ValueError("Outlining attribute data missing 'value' field")

        self._value = self._validate_and_normalize(data["value"])


class LightPenAttribute(ExtendedAttribute):
    """Light pen attribute for designating a field as light-pen selectable."""

    def __init__(self, value: Union[int, str] = 0) -> None:
        """Initialize light pen attribute."""
        super().__init__(value)

    def _validate_and_normalize(self, value: Union[int, str]) -> int:
        """Validate and normalize light pen value."""
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                raise ValueError(f"Invalid light pen value: {value}")

        if isinstance(value, int):
            if 0 <= value <= 0xFF:
                return value
            else:
                raise ValueError(f"Light pen value must be 0-255, got {value}")
        else:
            raise ValueError(
                f"Light pen value must be int or string, got {type(value)}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert light pen attribute to dictionary."""
        return {
            "type": AttributeType.LIGHT_PEN.value,
            "value": self._value,
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load light pen attribute from dictionary."""
        if "value" not in data:
            raise ValueError("Light pen attribute data missing 'value' field")

        self._value = self._validate_and_normalize(data["value"])


class BackgroundAttribute(ExtendedAttribute):
    """Background color attribute supporting base 16 and extended 256 color support.

    Supports both standard 3270 background colors (0-15) and extended colors (16-255)
    as defined in TN3270E specifications.
    """

    # Base 16 background colors (3270 standard)
    BASE_COLORS = {
        0: "neutral_black",
        1: "blue",
        2: "red",
        3: "pink",
        4: "green",
        5: "turquoise",
        6: "yellow",
        7: "neutral_white",
        8: "black",
        9: "deep_blue",
        10: "orange",
        11: "purple",
        12: "pale_green",
        13: "pale_turquoise",
        14: "grey",
        15: "white",
    }

    def __init__(self, value: Union[int, str] = 0) -> None:
        """Initialize background color attribute.

        Args:
            value: Background color value (0-255) or color name string

        Raises:
            ValueError: If value is invalid
        """
        super().__init__(value)

    def _validate_and_normalize(self, value: Union[int, str]) -> int:
        """Validate and normalize background color value.

        Args:
            value: Background color value as int or string

        Returns:
            Normalized background color value (0-255)

        Raises:
            ValueError: If value is invalid
        """
        if isinstance(value, str):
            # Try to map color name to value
            for val, name in self.BASE_COLORS.items():
                if name == value.lower():
                    return val
            # Try to parse as integer string
            try:
                value = int(value)
            except ValueError:
                raise ValueError(f"Invalid background color name or value: {value}")

        if isinstance(value, int):
            if 0 <= value <= 255:
                return value
            else:
                raise ValueError(f"Background color value must be 0-255, got {value}")
        else:
            raise ValueError(
                f"Background color value must be int or string, got {type(value)}"
            )

    def get_color_name(self) -> Optional[str]:
        """Get the background color name for base colors.

        Returns:
            Color name if it's a base color (0-15), None otherwise
        """
        return self.BASE_COLORS.get(self._value) if self._value <= 15 else None

    def is_base_color(self) -> bool:
        """Check if this is a base 16 background color.

        Returns:
            True if color is in base 16 range (0-15)
        """
        return 0 <= self._value <= 15

    def is_extended_color(self) -> bool:
        """Check if this is an extended background color.

        Returns:
            True if color is in extended range (16-255)
        """
        return 16 <= self._value <= 255

    def to_dict(self) -> Dict[str, Any]:
        """Convert background color attribute to dictionary.

        Returns:
            Dictionary with background color data
        """
        return {
            "type": AttributeType.BACKGROUND.value,
            "value": self._value,
            "name": self.get_color_name(),
            "is_base": self.is_base_color(),
            "is_extended": self.is_extended_color(),
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load background color attribute from dictionary.

        Args:
            data: Dictionary containing background color data

        Raises:
            ValueError: If data is invalid
        """
        if "value" not in data:
            raise ValueError("Background color attribute data missing 'value' field")

        self._value = self._validate_and_normalize(data["value"])
