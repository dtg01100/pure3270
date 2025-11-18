"""
Categorized warning infrastructure for Pure3270.

This module provides the core functionality for categorized warnings,
including filtering, configuration, and integration with the logging system.
"""

import logging
import sys
from typing import Any, Dict, List, Optional

from .categories import WarningCategory, WarningFilters, get_warning_filters

logger = logging.getLogger(__name__)


class CategorizedLogger:
    """A logger that supports categorized warnings with filtering."""

    def __init__(
        self, logger: logging.Logger, filters: Optional[WarningFilters] = None
    ) -> None:
        """Initialize categorized logger.

        Args:
            logger: The underlying logger instance
            filters: Warning filters to use (uses global filters if None)
        """
        self._logger = logger
        self._filters = filters or get_warning_filters()

    @property
    def logger(self) -> logging.Logger:
        """Get the underlying logger instance."""
        return self._logger

    def warning(self, category: WarningCategory, message: str, **kwargs: Any) -> None:
        """Log a categorized warning.

        Args:
            category: The warning category
            message: The warning message
            **kwargs: Additional arguments for the underlying logger
        """
        if self._filters.should_log(category, logging.WARNING):
            formatted_message = f"[{category.value.upper()}] {message}"
            self._logger.warning(formatted_message, **kwargs)

    def info(self, category: WarningCategory, message: str, **kwargs: Any) -> None:
        """Log a categorized info message.

        Args:
            category: The message category
            message: The info message
            **kwargs: Additional arguments for the underlying logger
        """
        if self._filters.should_log(category, logging.INFO):
            formatted_message = f"[{category.value.upper()}] {message}"
            self._logger.info(formatted_message, **kwargs)

    def error(self, category: WarningCategory, message: str, **kwargs: Any) -> None:
        """Log a categorized error message.

        Args:
            category: The error category
            message: The error message
            **kwargs: Additional arguments for the underlying logger
        """
        if self._filters.should_log(category, logging.ERROR):
            formatted_message = f"[{category.value.upper()}] {message}"
            self._logger.error(formatted_message, **kwargs)

    def debug(self, category: WarningCategory, message: str, **kwargs: Any) -> None:
        """Log a categorized debug message.

        Args:
            category: The debug category
            message: The debug message
            **kwargs: Additional arguments for the underlying logger
        """
        if self._filters.should_log(category, logging.DEBUG):
            formatted_message = f"[{category.value.upper()}] {message}"
            self._logger.debug(formatted_message, **kwargs)

    def critical(self, category: WarningCategory, message: str, **kwargs: Any) -> None:
        """Log a categorized critical message.

        Args:
            category: The critical message category
            message: The critical message
            **kwargs: Additional arguments for the underlying logger
        """
        if self._filters.should_log(category, logging.CRITICAL):
            formatted_message = f"[{category.value.upper()}] {message}"
            self._logger.critical(formatted_message, **kwargs)

    def log_protocol_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for protocol negotiation warnings."""
        self.warning(WarningCategory.PROTOCOL_NEGOTIATION, message, **kwargs)

    def log_data_stream_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for data stream warnings."""
        self.warning(WarningCategory.DATA_STREAM, message, **kwargs)

    def log_configuration_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for configuration warnings."""
        self.warning(WarningCategory.CONFIGURATION, message, **kwargs)

    def log_performance_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for performance warnings."""
        self.warning(WarningCategory.PERFORMANCE, message, **kwargs)

    def log_security_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for security warnings."""
        self.warning(WarningCategory.SECURITY, message, **kwargs)

    def log_parsing_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for parsing warnings."""
        self.warning(WarningCategory.PARSING, message, **kwargs)

    def log_state_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for state management warnings."""
        self.warning(WarningCategory.STATE_MANAGEMENT, message, **kwargs)

    def log_network_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for network warnings."""
        self.warning(WarningCategory.NETWORK, message, **kwargs)

    def log_ssl_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for SSL/TLS warnings."""
        self.warning(WarningCategory.SSL_TLS, message, **kwargs)

    def log_printer_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for printer warnings."""
        self.warning(WarningCategory.PRINTER, message, **kwargs)

    def log_file_transfer_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for file transfer warnings."""
        self.warning(WarningCategory.FILE_TRANSFER, message, **kwargs)

    def log_recovery_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for recovery warnings."""
        self.warning(WarningCategory.RECOVERY, message, **kwargs)

    def log_timeout_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for timeout warnings."""
        self.warning(WarningCategory.TIMEOUT, message, **kwargs)

    def log_validation_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for validation warnings."""
        self.warning(WarningCategory.VALIDATION, message, **kwargs)

    def log_unknown_data_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for unknown data warnings."""

    def log_style_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for style warnings."""
        self.warning(WarningCategory.STYLE, message, **kwargs)

    def log_deprecation_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for deprecation warnings."""
        self.warning(WarningCategory.DEPRECATION, message, **kwargs)

    def log_addressing_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for addressing warnings."""
        self.warning(WarningCategory.ADDRESSING, message, **kwargs)

    def log_sna_response_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for SNA response warnings."""
        self.warning(WarningCategory.SNA_RESPONSE, message, **kwargs)

    def log_external_api_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for external API warnings."""
        self.warning(WarningCategory.EXTERNAL_API, message, **kwargs)

    def log_resource_usage_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for resource usage warnings."""
        self.warning(WarningCategory.RESOURCE_USAGE, message, **kwargs)

    def log_state_management_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for state management warnings."""
        self.warning(WarningCategory.STATE_MANAGEMENT, message, **kwargs)

    def log_printing_warning(self, message: str, **kwargs: Any) -> None:
        """Convenience method for printing warnings."""
        self.warning(WarningCategory.PRINTING, message, **kwargs)
        self.warning(WarningCategory.UNKNOWN_DATA, message, **kwargs)


def get_categorized_logger(
    name: str, filters: Optional[WarningFilters] = None
) -> CategorizedLogger:
    """Get a categorized logger by name.

    Args:
        name: Logger name
        filters: Optional warning filters to use

    Returns:
        A categorized logger instance
    """
    logger = logging.getLogger(name)
    return CategorizedLogger(logger, filters)


def setup_default_warning_filters(environment: str = "development") -> WarningFilters:
    """Setup default warning filters based on environment.

    Args:
        environment: Environment type ('development', 'production', 'protocol_debug')

    Returns:
        Configured warning filters
    """
    from pure3270.warnings.categories import (
        configure_default_filters,
        create_production_filter,
        create_protocol_filter,
    )

    if environment == "development":
        configure_default_filters()
        return get_warning_filters()
    elif environment == "protocol_debug":
        return create_protocol_filter()
    elif environment == "production":
        return create_production_filter()
    else:
        configure_default_filters()
        return get_warning_filters()


def configure_logging_with_filters(
    level: int = logging.WARNING,
    environment: str = "development",
    format_string: Optional[str] = None,
) -> None:
    """Configure Python logging with categorized warnings support.

    Args:
        level: Base logging level
        environment: Environment type for filter configuration
        format_string: Custom format string for log messages
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure basic logging
    logging.basicConfig(level=level, format=format_string, stream=sys.stdout)

    # Setup warning filters based on environment
    setup_default_warning_filters(environment)


def add_warning_arguments(parser: Any) -> None:
    """Add command-line arguments for warning configuration.

    Args:
        parser: ArgumentParser instance
    """
    parser.add_argument(
        "--warning-filters",
        choices=["development", "production", "protocol_debug"],
        default="development",
        help="Warning filter preset to use",
    )

    parser.add_argument(
        "--disable-warning-categories",
        nargs="*",
        default=[],
        help="Warning categories to disable (e.g., style performance)",
    )

    parser.add_argument(
        "--enable-warning-categories",
        nargs="*",
        default=[],
        help="Warning categories to enable (overrides presets)",
    )

    parser.add_argument(
        "--warning-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="WARNING",
        help="Minimum logging level for warnings",
    )


def configure_warnings_from_args(args: Any) -> WarningFilters:
    """Configure warning filters from parsed command-line arguments.

    Args:
        args: Parsed command-line arguments

    Returns:
        Configured warning filters
    """
    from pure3270.warnings.categories import WarningCategory

    # Start with environment preset
    filters = setup_default_warning_filters(
        getattr(args, "warning_filters", "development")
    )

    # Apply custom category disabling
    disable_categories = getattr(args, "disable_warning_categories", [])
    for category_name in disable_categories:
        try:
            category = WarningCategory(category_name.lower())
            filters.disable_category(category)
        except ValueError:
            logger.warning(f"Unknown warning category: {category_name}")

    # Apply custom category enabling
    enable_categories = getattr(args, "enable_warning_categories", [])
    for category_name in enable_categories:
        try:
            category = WarningCategory(category_name.lower())
            filters.enable_category(category)
        except ValueError:
            logger.warning(f"Unknown warning category: {category_name}")

    return filters


def get_warning_statistics() -> Dict[str, Any]:
    """Get statistics about current warning configuration.

    Returns:
        Dictionary containing warning statistics
    """
    filters = get_warning_filters()

    return {
        "enabled_categories": [cat.value for cat in filters.get_enabled_categories()],
        "disabled_categories": [cat.value for cat in filters.get_disabled_categories()],
        "custom_levels": {
            cat.value: level for cat, level in filters._custom_levels.items()
        },
        "total_categories": len(WarningCategory),
        "environment_recommendations": {
            "development": "All warnings enabled, style warnings disabled",
            "production": "Only critical warnings enabled, raised to ERROR level",
            "protocol_debug": "Protocol-related warnings enabled, framework warnings disabled",
        },
    }
