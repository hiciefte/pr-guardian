"""Translation Processing Service for applying changes."""

import logging
from pathlib import Path

from src.lib.parsers.unified import (
    parse_translation_file,
    validate_translation_syntax,
    write_translation_file,
)
from src.models import TranslationChange

logger = logging.getLogger(__name__)


def apply_translation_change(
    change: TranslationChange,
    repo_path: Path,
) -> bool:
    """
    Apply a translation change to a file.

    Reads the translation file, updates the specified key,
    and writes back with validation.

    Args:
        change: Translation change to apply
        repo_path: Path to repository root

    Returns:
        True if change applied successfully, False otherwise

    Example:
        change = TranslationChange(
            file_path="src/i18n/es_ES.json",
            translation_key="greeting",
            original_value="Hola",
            new_value="Hola!",
            locale="es_ES",
            change_type=ChangeType.FIX,
            comment_id=123,
        )
        success = apply_translation_change(change, Path("/repo"))
    """
    file_path = repo_path / change.file_path

    # Validate before applying
    valid, error = validate_change_before_apply(change)
    if not valid:
        logger.error(f"Validation failed for {change.file_path}: {error}")
        return False

    # Check file exists
    if not file_path.exists():
        logger.error(f"Translation file not found: {file_path}")
        return False

    try:
        # Parse existing file
        translations = parse_translation_file(file_path)

        # Find and update the key
        if not _update_translation_key(
            translations,
            change.translation_key,
            change.original_value,
            change.new_value,
        ):
            logger.error(
                f"Key '{change.translation_key}' not found or "
                f"original value doesn't match in {file_path}"
            )
            return False

        # Write updated file
        write_translation_file(file_path, translations)

        # Validate syntax after write
        valid, error = validate_translation_syntax(file_path)
        if not valid:
            logger.error(f"Syntax validation failed after write: {error}")
            # Attempt to restore (would need backup, skipping for now)
            return False

        logger.info(
            f"Applied change to '{change.translation_key}' in {file_path}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to apply change to {file_path}: {e}")
        return False


def validate_change_before_apply(
    change: TranslationChange,
) -> tuple[bool, str]:
    """
    Validate a translation change before applying.

    Checks placeholder integrity, locale format, and file format support.

    Args:
        change: Translation change to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check placeholder integrity
    placeholder_valid, placeholder_error = change.validate_placeholders()
    if not placeholder_valid:
        return False, f"Placeholder integrity error: {placeholder_error}"

    # Check values are different
    if change.original_value == change.new_value:
        return False, "Original and new values are identical"

    # Check for empty values
    if not change.new_value.strip():
        return False, "New value cannot be empty"

    # Check file extension is supported
    supported = [".properties", ".json", ".yml", ".yaml"]
    if change.file_extension not in supported:
        return (
            False,
            f"Unsupported file format: {change.file_extension}. "
            f"Supported: {supported}",
        )

    return True, ""


def _update_translation_key(
    translations: dict,
    key: str,
    original_value: str,
    new_value: str,
) -> bool:
    """
    Update a translation key in the translations dictionary.

    Handles nested keys using dot notation.

    Args:
        translations: Dictionary of translations
        key: Translation key (may use dot notation for nesting)
        original_value: Expected original value for verification
        new_value: New value to set

    Returns:
        True if key found and updated, False otherwise
    """
    # Handle nested keys
    if "." in key:
        return _update_nested_key(translations, key, original_value, new_value)

    # Simple key
    if key not in translations:
        return False

    current_value = translations[key]
    if not isinstance(current_value, str):
        # Value is nested object, not a string
        return False

    # Verify original value matches (with some flexibility)
    if not _values_match(current_value, original_value):
        logger.warning(
            f"Original value mismatch for key '{key}': "
            f"expected '{original_value}', found '{current_value}'"
        )
        return False

    translations[key] = new_value
    return True


def _update_nested_key(
    translations: dict,
    key: str,
    original_value: str,
    new_value: str,
) -> bool:
    """
    Update a nested translation key using dot notation.

    Args:
        translations: Dictionary of translations
        key: Dot-notation key (e.g., "messages.greeting.hello")
        original_value: Expected original value
        new_value: New value to set

    Returns:
        True if key found and updated, False otherwise
    """
    parts = key.split(".")
    current = translations

    # Navigate to parent
    for part in parts[:-1]:
        if not isinstance(current, dict):
            return False
        if part not in current:
            return False
        current = current[part]

    # Update final key
    final_key = parts[-1]
    if not isinstance(current, dict) or final_key not in current:
        return False

    current_value = current[final_key]
    if not isinstance(current_value, str):
        return False

    if not _values_match(current_value, original_value):
        logger.warning(
            f"Original value mismatch for nested key '{key}': "
            f"expected '{original_value}', found '{current_value}'"
        )
        return False

    current[final_key] = new_value
    return True


def _values_match(actual: str, expected: str) -> bool:
    """
    Check if two translation values match.

    Allows for minor whitespace differences.

    Args:
        actual: Actual value in file
        expected: Expected value

    Returns:
        True if values match
    """
    # Exact match
    if actual == expected:
        return True

    # Normalize whitespace
    actual_normalized = " ".join(actual.split())
    expected_normalized = " ".join(expected.split())

    return actual_normalized == expected_normalized


def preview_change(
    change: TranslationChange,
    repo_path: Path,
) -> dict | None:
    """
    Preview a translation change without applying it.

    Args:
        change: Translation change to preview
        repo_path: Path to repository root

    Returns:
        Preview dict or None if file cannot be read
    """
    file_path = repo_path / change.file_path

    if not file_path.exists():
        return None

    try:
        translations = parse_translation_file(file_path)

        # Find current value
        current_value = _get_nested_value(translations, change.translation_key)

        return {
            "file_path": str(file_path),
            "key": change.translation_key,
            "current_value": current_value,
            "original_value": change.original_value,
            "new_value": change.new_value,
            "values_match": _values_match(
                current_value or "",
                change.original_value,
            ),
        }

    except Exception as e:
        logger.error(f"Failed to preview change: {e}")
        return None


def _get_nested_value(translations: dict, key: str) -> str | None:
    """
    Get a value from nested translations using dot notation.

    Args:
        translations: Dictionary of translations
        key: Dot-notation key

    Returns:
        Value if found, None otherwise
    """
    if "." not in key:
        value = translations.get(key)
        return value if isinstance(value, str) else None

    parts = key.split(".")
    current = translations

    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]

    return current if isinstance(current, str) else None


def batch_apply_changes(
    changes: list[TranslationChange],
    repo_path: Path,
) -> tuple[list[TranslationChange], list[TranslationChange]]:
    """
    Apply multiple translation changes.

    Args:
        changes: List of translation changes to apply
        repo_path: Path to repository root

    Returns:
        Tuple of (successful_changes, failed_changes)
    """
    successful: list[TranslationChange] = []
    failed: list[TranslationChange] = []

    for change in changes:
        if apply_translation_change(change, repo_path):
            successful.append(change)
        else:
            failed.append(change)

    logger.info(
        f"Applied {len(successful)}/{len(changes)} changes "
        f"({len(failed)} failed)"
    )

    return successful, failed
