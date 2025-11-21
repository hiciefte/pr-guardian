"""JSON translation file parser with schema validation."""

import json
from pathlib import Path
from typing import Any

from jsonschema import ValidationError, validate

# Schema for flat translation JSON files
TRANSLATION_JSON_SCHEMA = {
    "type": "object",
    "patternProperties": {
        "^[a-zA-Z0-9_.-]+$": {
            "oneOf": [
                {"type": "string"},
                {"type": "object"}  # Allow nested structures
            ]
        }
    },
    "additionalProperties": False
}

# Schema for nested translation JSON files (more permissive)
NESTED_TRANSLATION_SCHEMA = {
    "type": "object",
    "additionalProperties": True
}


def parse_json_translation(
    file_path: Path | str,
    validate_schema: bool = True
) -> dict[str, Any]:
    """
    Parse JSON translation file with optional schema validation.

    Args:
        file_path: Path to JSON translation file
        validate_schema: Whether to validate against translation schema

    Returns:
        Dictionary of translation data

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
        jsonschema.ValidationError: If schema validation fails

    Example:
        translations = parse_json_translation("en_US.json")
        print(translations["greeting"])  # "Hello"
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if validate_schema:
        # Try strict schema first, fall back to nested
        try:
            validate(instance=data, schema=TRANSLATION_JSON_SCHEMA)
        except ValidationError:
            validate(instance=data, schema=NESTED_TRANSLATION_SCHEMA)

    return data


def write_json_translation(
    file_path: Path | str,
    translations: dict[str, Any],
    indent: int = 2,
    sort_keys: bool = False
) -> None:
    """
    Write JSON translation file with formatting.

    Args:
        file_path: Path to write JSON file
        translations: Dictionary of translation data
        indent: JSON indentation level (default: 2)
        sort_keys: Whether to sort keys alphabetically

    Raises:
        IOError: If file cannot be written

    Example:
        write_json_translation(
            "en_US.json",
            {"greeting": "Hello", "farewell": "Goodbye"}
        )
    """
    file_path = Path(file_path)

    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(
            translations,
            f,
            ensure_ascii=False,
            indent=indent,
            sort_keys=sort_keys
        )
        # Ensure trailing newline
        f.write("\n")


def validate_json_syntax(file_path: Path | str) -> tuple[bool, str]:
    """
    Validate JSON file syntax and structure.

    Args:
        file_path: Path to JSON file

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        valid, error = validate_json_syntax("translations.json")
        if not valid:
            print(f"Validation error: {error}")
    """
    try:
        parse_json_translation(file_path)
        return True, ""
    except FileNotFoundError as e:
        return False, str(e)
    except json.JSONDecodeError as e:
        return False, f"JSON syntax error at line {e.lineno}, column {e.colno}: {e.msg}"
    except ValidationError as e:
        return False, f"Schema validation error: {e.message}"
    except Exception as e:
        return False, f"Unexpected error: {e}"
