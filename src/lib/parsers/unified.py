"""Unified parser interface for multiple translation file formats."""

from pathlib import Path
from typing import Any

from .json_parser import (
    parse_json_translation,
    validate_json_syntax,
    write_json_translation,
)
from .properties import (
    parse_properties_file,
    validate_properties_syntax,
    write_properties_file,
)
from .yaml_parser import (
    parse_yaml_translation,
    validate_yaml_syntax,
    write_yaml_translation,
)


def parse_translation_file(file_path: Path | str) -> dict[str, Any]:
    """
    Parse translation file based on extension.

    Auto-detects format from file extension and uses
    appropriate parser.

    Supported formats:
    - .properties (Java properties)
    - .json (JSON)
    - .yml, .yaml (YAML)

    Args:
        file_path: Path to translation file

    Returns:
        Dictionary of translation data

    Raises:
        ValueError: If file format is not supported
        FileNotFoundError: If file doesn't exist

    Example:
        translations = parse_translation_file("messages_es.properties")
        translations = parse_translation_file("en_US.json")
        translations = parse_translation_file("translations.yml")
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    parsers = {
        ".properties": parse_properties_file,
        ".json": parse_json_translation,
        ".yml": parse_yaml_translation,
        ".yaml": parse_yaml_translation,
    }

    parser = parsers.get(suffix)
    if parser is None:
        supported = ", ".join(parsers.keys())
        raise ValueError(
            f"Unsupported translation file format: {suffix}. "
            f"Supported formats: {supported}"
        )

    return parser(file_path)


def write_translation_file(
    file_path: Path | str,
    translations: dict[str, Any]
) -> None:
    """
    Write translation file based on extension.

    Auto-detects format from file extension and uses
    appropriate writer.

    Args:
        file_path: Path to translation file
        translations: Dictionary of translation data

    Raises:
        ValueError: If file format is not supported
        IOError: If file cannot be written

    Example:
        write_translation_file(
            "messages_es.properties",
            {"greeting": "Hola"}
        )
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    writers = {
        ".properties": write_properties_file,
        ".json": write_json_translation,
        ".yml": write_yaml_translation,
        ".yaml": write_yaml_translation,
    }

    writer = writers.get(suffix)
    if writer is None:
        supported = ", ".join(writers.keys())
        raise ValueError(
            f"Unsupported translation file format: {suffix}. "
            f"Supported formats: {supported}"
        )

    writer(file_path, translations)


def validate_translation_syntax(file_path: Path | str) -> tuple[bool, str]:
    """
    Validate translation file syntax based on extension.

    Args:
        file_path: Path to translation file

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        valid, error = validate_translation_syntax("messages.json")
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


def get_supported_formats() -> list[str]:
    """
    Get list of supported translation file formats.

    Returns:
        List of supported file extensions
    """
    return [".properties", ".json", ".yml", ".yaml"]


def detect_format(file_path: Path | str) -> str | None:
    """
    Detect translation file format from extension.

    Args:
        file_path: Path to translation file

    Returns:
        Format name or None if not supported
    """
    suffix = Path(file_path).suffix.lower()

    format_map = {
        ".properties": "properties",
        ".json": "json",
        ".yml": "yaml",
        ".yaml": "yaml",
    }

    return format_map.get(suffix)
