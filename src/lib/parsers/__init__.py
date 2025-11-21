"""Translation file parsers for PR Guardian."""

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
from .unified import (
    detect_format,
    get_supported_formats,
    parse_translation_file,
    validate_translation_syntax,
    write_translation_file,
)
from .yaml_parser import (
    parse_yaml_translation,
    validate_yaml_syntax,
    write_yaml_translation,
)

__all__ = [
    # properties
    "parse_properties_file",
    "validate_properties_syntax",
    "write_properties_file",
    # json
    "parse_json_translation",
    "validate_json_syntax",
    "write_json_translation",
    # yaml
    "parse_yaml_translation",
    "validate_yaml_syntax",
    "write_yaml_translation",
    # unified
    "detect_format",
    "get_supported_formats",
    "parse_translation_file",
    "validate_translation_syntax",
    "write_translation_file",
]
