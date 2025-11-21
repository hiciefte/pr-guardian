"""YAML translation file parser with safe loading."""

from pathlib import Path
from typing import Any

import yaml


def parse_yaml_translation(file_path: Path | str) -> dict[str, Any]:
    """
    Parse YAML translation file safely.

    Uses yaml.safe_load() to prevent arbitrary code execution
    from malicious YAML files.

    Args:
        file_path: Path to YAML translation file

    Returns:
        Dictionary of translation data

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML is invalid

    Example:
        translations = parse_yaml_translation("messages.yml")
        print(translations["en"]["greeting"])  # "Hello"
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"YAML file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        # Use safe_load to prevent code execution
        data = yaml.safe_load(f)

    # Handle empty files
    if data is None:
        return {}

    return data


def write_yaml_translation(
    file_path: Path | str,
    translations: dict[str, Any],
    default_flow_style: bool = False,
    sort_keys: bool = False
) -> None:
    """
    Write YAML translation file preserving structure.

    Args:
        file_path: Path to write YAML file
        translations: Dictionary of translation data
        default_flow_style: Use flow style for collections
        sort_keys: Whether to sort keys alphabetically

    Raises:
        IOError: If file cannot be written

    Example:
        write_yaml_translation(
            "messages.yml",
            {"en": {"greeting": "Hello"}}
        )
    """
    file_path = Path(file_path)

    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(
            translations,
            f,
            allow_unicode=True,
            default_flow_style=default_flow_style,
            sort_keys=sort_keys,
            width=1000  # Prevent unwanted line wrapping
        )


def validate_yaml_syntax(file_path: Path | str) -> tuple[bool, str]:
    """
    Validate YAML file syntax.

    Args:
        file_path: Path to YAML file

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        valid, error = validate_yaml_syntax("translations.yml")
        if not valid:
            print(f"YAML error: {error}")
    """
    try:
        parse_yaml_translation(file_path)
        return True, ""
    except FileNotFoundError as e:
        return False, str(e)
    except yaml.YAMLError as e:
        # Extract line/column info if available
        if hasattr(e, 'problem_mark') and e.problem_mark:
            mark = e.problem_mark
            return False, (
                f"YAML syntax error at line {mark.line + 1}, "
                f"column {mark.column + 1}: {e.problem}"
            )
        return False, f"YAML syntax error: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"
