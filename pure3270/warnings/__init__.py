"""
Pure3270 warning categorization system.

This package provides categorized warnings for the Pure3270 framework,
allowing users to distinguish between different types of warnings
and filter them appropriately.
"""

from .categories import (
    WarningCategory,
    WarningFilters,
    configure_default_filters,
    create_production_filter,
    create_protocol_filter,
    get_category_recommendations,
    get_warning_filters,
)
from .infrastructure import (
    CategorizedLogger,
    add_warning_arguments,
    configure_logging_with_filters,
    configure_warnings_from_args,
    get_categorized_logger,
    get_warning_statistics,
    setup_default_warning_filters,
)

__all__ = [
    # Categories
    "WarningCategory",
    "WarningFilters",
    "get_warning_filters",
    "configure_default_filters",
    "create_protocol_filter",
    "create_production_filter",
    "get_category_recommendations",
    # Infrastructure
    "CategorizedLogger",
    "get_categorized_logger",
    "setup_default_warning_filters",
    "configure_logging_with_filters",
    "add_warning_arguments",
    "configure_warnings_from_args",
    "get_warning_statistics",
]

# Initialize default filters on import
configure_default_filters()
