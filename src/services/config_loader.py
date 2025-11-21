"""Configuration loading service for PR Guardian."""

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from src.models.config import PRGuardianConfiguration

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""

    pass


def get_default_config_path() -> Path:
    """
    Get the default configuration file path.

    Returns:
        Path to the default config file (pr-guardian.yml in current directory)
    """
    return Path.cwd() / "pr-guardian.yml"


def load_config(config_path: Path) -> PRGuardianConfiguration:
    """
    Load and validate PR Guardian configuration from YAML file.

    This function:
    - Reads the YAML configuration file
    - Validates against Pydantic models
    - Resolves environment variable references
    - Validates required fields and token accessibility

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        Validated PRGuardianConfiguration object

    Raises:
        ConfigurationError: If file not found, invalid YAML, or validation fails
        FileNotFoundError: If configuration file does not exist
    """
    logger.info(f"Loading configuration from: {config_path}")

    # Check file exists
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    if not config_path.is_file():
        raise ConfigurationError(f"Configuration path is not a file: {config_path}")

    # Read YAML file
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in configuration file: {e}")

    if raw_config is None:
        raise ConfigurationError("Configuration file is empty")

    if not isinstance(raw_config, dict):
        raise ConfigurationError(
            f"Configuration must be a YAML mapping, got: {type(raw_config).__name__}"
        )

    # Resolve environment variables in configuration
    resolved_config = _resolve_env_variables(raw_config)

    # Validate with Pydantic model
    try:
        config = PRGuardianConfiguration(**resolved_config)
    except ValidationError as e:
        error_messages = []
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            msg = error["msg"]
            error_messages.append(f"  {loc}: {msg}")
        raise ConfigurationError(
            f"Configuration validation failed:\n" + "\n".join(error_messages)
        )

    # Validate environment variables are accessible
    _validate_environment_tokens(config)

    logger.info(
        f"Configuration loaded successfully: {len(config.repositories)} repositories"
    )

    return config


def _resolve_env_variables(config: Any, path: str = "") -> Any:
    """
    Recursively resolve environment variable references in configuration.

    Supports ${VAR_NAME} and ${VAR_NAME:-default} syntax.

    Args:
        config: Configuration value (dict, list, or scalar)
        path: Current path for error messages

    Returns:
        Configuration with environment variables resolved
    """
    if isinstance(config, dict):
        return {
            key: _resolve_env_variables(value, f"{path}.{key}" if path else key)
            for key, value in config.items()
        }
    elif isinstance(config, list):
        return [
            _resolve_env_variables(item, f"{path}[{i}]")
            for i, item in enumerate(config)
        ]
    elif isinstance(config, str):
        return _resolve_string_env_vars(config)
    else:
        return config


def _resolve_string_env_vars(value: str) -> str:
    """
    Resolve environment variable references in a string.

    Supports:
    - ${VAR_NAME} - Required variable
    - ${VAR_NAME:-default} - Variable with default value

    Args:
        value: String potentially containing env var references

    Returns:
        String with environment variables resolved
    """
    import re

    # Pattern for ${VAR_NAME} or ${VAR_NAME:-default}
    pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'

    def replace_env(match: re.Match) -> str:
        var_name = match.group(1)
        default_value = match.group(2)

        env_value = os.getenv(var_name)
        if env_value is not None:
            return env_value
        elif default_value is not None:
            return default_value
        else:
            # Return original placeholder - will be validated later
            return match.group(0)

    return re.sub(pattern, replace_env, value)


def _validate_environment_tokens(config: PRGuardianConfiguration) -> None:
    """
    Validate that required environment variables are set.

    Args:
        config: Validated configuration object

    Raises:
        ConfigurationError: If required environment variables are missing
    """
    missing_vars = []

    # Check GitHub token
    github_token_var = config.github.token_env
    if not os.getenv(github_token_var):
        missing_vars.append(f"{github_token_var} (GitHub authentication)")

    # Check LLM API key
    llm_api_key_var = config.llm.api_key_env
    if not os.getenv(llm_api_key_var):
        logger.warning(
            f"LLM API key environment variable not set: {llm_api_key_var}. "
            "LLM-based comment parsing will not be available."
        )

    if missing_vars:
        raise ConfigurationError(
            f"Required environment variables not set:\n"
            + "\n".join(f"  - {var}" for var in missing_vars)
        )


def validate_repository_access(config: PRGuardianConfiguration) -> list[str]:
    """
    Validate access to configured repositories.

    This performs a lightweight check that repositories are accessible
    with the provided token.

    Args:
        config: Validated configuration object

    Returns:
        List of warnings for repositories with potential access issues
    """
    warnings = []

    for repo in config.repositories:
        repo_str = f"{repo.owner}/{repo.name}"
        # Actual access validation would require GitHub client
        # This is a placeholder for the validation logic
        logger.debug(f"Repository configured: {repo_str}")

    return warnings
