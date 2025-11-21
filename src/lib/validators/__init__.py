"""Validators for PR Guardian."""

from .placeholder import (
    PLACEHOLDER_PATTERNS,
    count_placeholders,
    extract_placeholders,
    get_placeholder_format,
    normalize_placeholders,
    validate_placeholder_integrity,
)
from .syntax import (
    get_validation_summary,
    validate_multiple_files,
    validate_translation_syntax,
)

__all__ = [
    # placeholder
    "PLACEHOLDER_PATTERNS",
    "count_placeholders",
    "extract_placeholders",
    "get_placeholder_format",
    "normalize_placeholders",
    "validate_placeholder_integrity",
    # syntax
    "get_validation_summary",
    "validate_multiple_files",
    "validate_translation_syntax",
]
