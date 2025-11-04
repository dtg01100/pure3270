"""
Warning categories for Pure3270 framework.

This module defines warning categories to help users distinguish between different
types of warnings in the Pure3270 framework, making it easier to understand
which warnings require immediate attention vs. those that are informational.
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Set


class WarningCategory(Enum):
    """Enumeration of warning categories."""

    # Protocol-related warnings (most critical)
    PROTOCOL_NEGOTIATION = "protocol_negotiation"  # TN3270E negotiation issues
    DATA_STREAM = "data_stream"  # Data parsing/format issues
    SNA_RESPONSE = "sna_response"  # SNA protocol issues
    ADDRESSING = "addressing"  # Screen addressing problems

    # Framework-related warnings (less critical)
    CONFIGURATION = "configuration"  # Invalid configurations
    DEPRECATION = "deprecation"  # Deprecated features
    STYLE = "style"  # Code style issues

    # Integration warnings (external systems)
    SSL_TLS = "ssl_tls"  # SSL/TLS related issues
    NETWORK = "network"  # Network connectivity issues
    EXTERNAL_API = "external_api"  # Third-party API issues

    # Performance warnings
    PERFORMANCE = "performance"  # Performance-related issues
    TIMEOUT = "timeout"  # Timeout-related issues
    RESOURCE_USAGE = "resource_usage"  # Resource consumption warnings

    # State management warnings
    STATE_MANAGEMENT = "state_management"  # Invalid state transitions
    RECOVERY = "recovery"  # Error recovery attempts
    VALIDATION = "validation"  # Validation failures

    # Security warnings
    SECURITY = "security"  # Security-related warnings

    # Printer-specific warnings
    PRINTER = "printer"  # Printer emulation issues
    PRINTING = "printing"  # Print job issues

    # File transfer warnings
    FILE_TRANSFER = "file_transfer"  # IND$FILE issues

    # Parser warnings
    PARSING = "parsing"  # General parsing issues
    UNKNOWN_DATA = "unknown_data"  # Unrecognized data formats


class WarningFilters:
    """Manages warning category filters."""

    def __init__(self) -> None:
        self._enabled_categories: Set[WarningCategory] = set(WarningCategory)
        self._disabled_categories: Set[WarningCategory] = set()
        self._custom_levels: Dict[WarningCategory, int] = {}

    def enable_category(self, category: WarningCategory) -> None:
        """Enable a warning category."""
        self._disabled_categories.discard(category)
        self._enabled_categories.add(category)

    def disable_category(self, category: WarningCategory) -> None:
        """Disable a warning category."""
        self._enabled_categories.discard(category)
        self._disabled_categories.add(category)

    def set_category_level(self, category: WarningCategory, level: int) -> None:
        """Set logging level for a specific category."""
        self._custom_levels[category] = level

    def is_category_enabled(self, category: WarningCategory) -> bool:
        """Check if a category is enabled."""
        return (
            category in self._enabled_categories
            and category not in self._disabled_categories
        )

    def should_log(self, category: WarningCategory, level: int) -> bool:
        """Determine if a warning should be logged."""
        if not self.is_category_enabled(category):
            return False

        custom_level = self._custom_levels.get(category)
        if custom_level is not None:
            return level >= custom_level

        return True

    def get_enabled_categories(self) -> Set[WarningCategory]:
        """Get all enabled categories."""
        return self._enabled_categories - self._disabled_categories

    def get_disabled_categories(self) -> Set[WarningCategory]:
        """Get all disabled categories."""
        return self._disabled_categories.copy()

    def reset(self) -> None:
        """Reset all filters to default (all enabled)."""
        self._enabled_categories = set(WarningCategory)
        self._disabled_categories = set()
        self._custom_levels.clear()


# Global warning filters instance
_global_warning_filters = WarningFilters()


def get_warning_filters() -> WarningFilters:
    """Get the global warning filters instance."""
    return _global_warning_filters


def configure_default_filters() -> None:
    """Configure default warning filters for common use cases."""
    filters = get_warning_filters()

    # By default, disable style warnings as they're usually not actionable
    filters.disable_category(WarningCategory.STYLE)

    # Enable all other categories by default
    for category in WarningCategory:
        if category != WarningCategory.STYLE:
            filters.enable_category(category)


def create_protocol_filter() -> WarningFilters:
    """Create filters optimized for protocol debugging."""
    filters: WarningFilters = WarningFilters()

    # Enable all protocol-related warnings
    filters.enable_category(WarningCategory.PROTOCOL_NEGOTIATION)
    filters.enable_category(WarningCategory.DATA_STREAM)
    filters.enable_category(WarningCategory.SNA_RESPONSE)
    filters.enable_category(WarningCategory.ADDRESSING)
    filters.enable_category(WarningCategory.PARSING)
    filters.enable_category(WarningCategory.UNKNOWN_DATA)

    # Disable framework and style warnings
    filters.disable_category(WarningCategory.CONFIGURATION)
    filters.disable_category(WarningCategory.DEPRECATION)
    filters.disable_category(WarningCategory.STYLE)
    filters.disable_category(WarningCategory.PERFORMANCE)
    filters.disable_category(WarningCategory.TIMEOUT)

    # Optionally enable security warnings
    filters.enable_category(WarningCategory.SECURITY)

    return filters


def create_production_filter() -> WarningFilters:
    """Create filters optimized for production use."""
    filters: WarningFilters = WarningFilters()

    # Enable critical protocol and security warnings
    filters.enable_category(WarningCategory.PROTOCOL_NEGOTIATION)
    filters.enable_category(WarningCategory.SECURITY)
    filters.enable_category(WarningCategory.STATE_MANAGEMENT)
    filters.enable_category(WarningCategory.RECOVERY)

    # Set protocol warnings to ERROR level in production
    filters.set_category_level(WarningCategory.PROTOCOL_NEGOTIATION, logging.ERROR)
    filters.set_category_level(WarningCategory.SECURITY, logging.ERROR)

    # Disable verbose warnings
    filters.disable_category(WarningCategory.PERFORMANCE)
    filters.disable_category(WarningCategory.TIMEOUT)
    filters.disable_category(WarningCategory.RESOURCE_USAGE)
    filters.disable_category(WarningCategory.STYLE)
    filters.disable_category(WarningCategory.DEPRECATION)

    return filters


def get_category_recommendations() -> Dict[str, str]:
    """Get recommendations for when to use each warning category."""
    return {
        WarningCategory.PROTOCOL_NEGOTIATION.value: "Use for TN3270E negotiation issues, handshake failures",
        WarningCategory.DATA_STREAM.value: "Use for data format errors, parsing failures",
        WarningCategory.SNA_RESPONSE.value: "Use for SNA protocol response issues",
        WarningCategory.ADDRESSING.value: "Use for screen addressing calculation errors",
        WarningCategory.CONFIGURATION.value: "Use for invalid configuration values",
        WarningCategory.DEPRECATION.value: "Use for deprecated feature usage",
        WarningCategory.STYLE.value: "Use for code style and formatting issues",
        WarningCategory.SSL_TLS.value: "Use for SSL/TLS certificate and encryption issues",
        WarningCategory.NETWORK.value: "Use for network connectivity problems",
        WarningCategory.EXTERNAL_API.value: "Use for third-party API issues",
        WarningCategory.PERFORMANCE.value: "Use for performance optimization warnings",
        WarningCategory.TIMEOUT.value: "Use for timeout-related issues",
        WarningCategory.RESOURCE_USAGE.value: "Use for resource consumption warnings",
        WarningCategory.STATE_MANAGEMENT.value: "Use for invalid state transitions",
        WarningCategory.RECOVERY.value: "Use for error recovery attempts",
        WarningCategory.VALIDATION.value: "Use for validation failures",
        WarningCategory.SECURITY.value: "Use for security-related warnings",
        WarningCategory.PRINTER.value: "Use for printer emulation issues",
        WarningCategory.PRINTING.value: "Use for print job issues",
        WarningCategory.FILE_TRANSFER.value: "Use for IND$FILE transfer issues",
        WarningCategory.PARSING.value: "Use for general parsing issues",
        WarningCategory.UNKNOWN_DATA.value: "Use for unrecognized data formats",
    }
