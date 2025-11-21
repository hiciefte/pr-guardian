"""Syntax validation for translation files."""

from pathlib import Path

from ..parsers.json_parser import validate_json_syntax
from ..parsers.properties import validate_properties_syntax
from ..parsers.yaml_parser import validate_yaml_syntax


def validate_translation_syntax(file_path: Path | str) -> tuple[bool, str]:
    """
    Validate translation file syntax based on extension.

    Unified interface that routes to format-specific validators.

    Supported formats:
    - .properties (Java properties)
    - .json (JSON)
    - .yml, .yaml (YAML)

    Args:
        file_path: Path to translation file

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        valid, error = validate_translation_syntax("messages_es.properties")
        if not valid:
            print(f"Syntax error: {error}")
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    validators = {
        ".properties": validate_properties_syntax,
        ".json": validate_json_syntax,
        ".yml": validate_yaml_syntax,
        ".yaml": validate_yaml_syntax,
    }

    validator = validators.get(suffix)
    if validator is None:
        supported = ", ".join(validators.keys())
        return False, (
            f"Unsupported format: {suffix}. "
            f"Supported formats: {supported}"
        )

    return validator(file_path)


def validate_multiple_files(
    file_paths: list[Path | str]
) -> dict[str, tuple[bool, str]]:
    """
    Validate multiple translation files.

    Args:
        file_paths: List of file paths to validate

    Returns:
        Dictionary mapping file paths to (is_valid, error_message)

    Example:
        results = validate_multiple_files([
            "en_US.json",
            "es_ES.json",
            "messages.properties"
        ])
        for path, (valid, error) in results.items():
            if not valid:
                print(f"{path}: {error}")
    """
    results = {}

    for file_path in file_paths:
        path_str = str(file_path)
        results[path_str] = validate_translation_syntax(file_path)

    return results


def get_validation_summary(
    results: dict[str, tuple[bool, str]]
) -> tuple[int, int, list[str]]:
    """
    Get summary of validation results.

    Args:
        results: Dictionary from validate_multiple_files

    Returns:
        Tuple of (valid_count, invalid_count, error_files)
    """
    valid_count = sum(1 for valid, _ in results.values() if valid)
    invalid_count = len(results) - valid_count
    error_files = [
        path for path, (valid, _) in results.items() if not valid
    ]

    return valid_count, invalid_count, error_files
