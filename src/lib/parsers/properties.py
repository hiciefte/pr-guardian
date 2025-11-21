"""Java .properties file parser using javaproperties library."""

from pathlib import Path

from javaproperties import dump, load


def parse_properties_file(file_path: Path | str) -> dict[str, str]:
    """
    Parse Java .properties file with full format support.

    Handles all Java escape sequences, Unicode characters,
    and preserves the original formatting.

    Args:
        file_path: Path to .properties file

    Returns:
        Dictionary of key-value translation pairs

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file cannot be parsed

    Example:
        translations = parse_properties_file("messages_es.properties")
        print(translations["greeting"])  # "Hola"
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Properties file not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return load(f)
    except UnicodeDecodeError:
        # Fallback to Latin-1 (Java default for .properties)
        with open(file_path, "r", encoding="latin-1") as f:
            return load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse properties file: {e}") from e


def write_properties_file(
    file_path: Path | str,
    translations: dict[str, str],
    comments: str | None = None
) -> None:
    """
    Write Java .properties file preserving format.

    Args:
        file_path: Path to write .properties file
        translations: Dictionary of key-value translation pairs
        comments: Optional header comments

    Raises:
        IOError: If file cannot be written

    Example:
        write_properties_file(
            "messages_es.properties",
            {"greeting": "Hola", "farewell": "Adios"}
        )
    """
    file_path = Path(file_path)

    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        dump(
            translations,
            f,
            ensure_ascii=False,
            comments=comments
        )


def validate_properties_syntax(file_path: Path | str) -> tuple[bool, str]:
    """
    Validate .properties file syntax.

    Args:
        file_path: Path to .properties file

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        valid, error = validate_properties_syntax("messages.properties")
        if not valid:
            print(f"Syntax error: {error}")
    """
    try:
        parse_properties_file(file_path)
        return True, ""
    except FileNotFoundError as e:
        return False, str(e)
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {e}"
