"""Placeholder validation for translation integrity."""

import re

# Placeholder patterns for various formats
PLACEHOLDER_PATTERNS = [
    r'\{[a-zA-Z0-9_]+\}',           # {variable}
    r'\{\{[a-zA-Z0-9_]+\}\}',       # {{key}}
    r'%[sd]',                        # %s, %d (printf-style)
    r'\$\{[a-zA-Z0-9_]+\}',         # ${variable}
    r'%\([a-zA-Z0-9_]+\)[sd]',      # %(name)s (Python)
    r'%[0-9]*\$[sd]',               # %1$s (positional printf)
    r'\{[0-9]+\}',                   # {0}, {1} (indexed)
]


def extract_placeholders(text: str) -> set[str]:
    """
    Extract all placeholders from translation text.

    Supports multiple placeholder formats:
    - {variable} - Simple curly brace
    - {{key}} - Double curly brace (e.g., Mustache)
    - %s, %d - Printf-style
    - ${variable} - Shell/JS style
    - %(name)s - Python style
    - %1$s - Positional printf
    - {0}, {1} - Indexed placeholders

    Args:
        text: Translation text to scan

    Returns:
        Set of placeholder strings found

    Example:
        placeholders = extract_placeholders("Hello {name}, you have %d messages")
        # Returns: {'{name}', '%d'}
    """
    placeholders: set[str] = set()

    for pattern in PLACEHOLDER_PATTERNS:
        matches = re.findall(pattern, text)
        placeholders.update(matches)

    return placeholders


def validate_placeholder_integrity(
    original: str,
    modified: str
) -> tuple[bool, str]:
    """
    Validate that placeholder variables are preserved in translation.

    Ensures that the modified translation contains exactly the same
    placeholders as the original, preventing runtime errors from
    missing or added variables.

    Args:
        original: Original translation text
        modified: Modified/translated text

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        valid, error = validate_placeholder_integrity(
            "Hello {name}!",
            "Hola {nombre}!"
        )
        # Returns: (False, "Missing placeholders: {'{name}'}; Added placeholders: {'{nombre}'}")
    """
    original_placeholders = extract_placeholders(original)
    modified_placeholders = extract_placeholders(modified)

    if original_placeholders == modified_placeholders:
        return True, ""

    missing = original_placeholders - modified_placeholders
    added = modified_placeholders - original_placeholders

    error_parts = []

    if missing:
        error_parts.append(f"Missing placeholders: {missing}")

    if added:
        error_parts.append(f"Added placeholders: {added}")

    return False, "; ".join(error_parts)


def count_placeholders(text: str) -> int:
    """
    Count total number of placeholders in text.

    Args:
        text: Text to analyze

    Returns:
        Number of placeholders found
    """
    return len(extract_placeholders(text))


def get_placeholder_format(placeholder: str) -> str | None:
    """
    Identify the format type of a placeholder.

    Args:
        placeholder: Placeholder string

    Returns:
        Format name or None if not recognized
    """
    format_patterns = [
        (r'^\{[a-zA-Z0-9_]+\}$', 'curly_brace'),
        (r'^\{\{[a-zA-Z0-9_]+\}\}$', 'double_curly'),
        (r'^%[sd]$', 'printf'),
        (r'^\$\{[a-zA-Z0-9_]+\}$', 'shell_style'),
        (r'^%\([a-zA-Z0-9_]+\)[sd]$', 'python_style'),
        (r'^%[0-9]*\$[sd]$', 'positional_printf'),
        (r'^\{[0-9]+\}$', 'indexed'),
    ]

    for pattern, format_name in format_patterns:
        if re.match(pattern, placeholder):
            return format_name

    return None


def normalize_placeholders(
    text: str,
    source_format: str,
    target_format: str
) -> str:
    """
    Convert placeholders from one format to another.

    Currently supports:
    - curly_brace <-> indexed

    Args:
        text: Text with placeholders
        source_format: Current placeholder format
        target_format: Desired placeholder format

    Returns:
        Text with converted placeholders

    Note:
        This is a basic implementation. Complex conversions
        may require additional context about variable names.
    """
    if source_format == target_format:
        return text

    # Example: Convert {name} to {0}, {count} to {1}
    if source_format == 'curly_brace' and target_format == 'indexed':
        placeholders = sorted(extract_placeholders(text))
        result = text
        for i, ph in enumerate(placeholders):
            result = result.replace(ph, f'{{{i}}}', 1)
        return result

    # Unsupported conversion
    return text
