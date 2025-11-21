"""Configuration management commands for PR Guardian CLI."""

import sys
from pathlib import Path

import click
import yaml

from src.lib.utils import configure_logging, get_logger
from src.services import load_config
from src.services.config_loader import ConfigurationError


logger = get_logger(__name__)


@click.group()
def config() -> None:
    """Configuration management commands."""
    pass


@config.command()
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    default="config/config.yml",
    help="Path to configuration file.",
    show_default=True,
)
def validate(config_path: Path) -> None:
    """Validate configuration file."""
    configure_logging()

    try:
        config = load_config(config_path)
        click.echo(click.style("Configuration is valid!", fg="green"))
        click.echo(f"  Repositories: {len(config.repositories)}")
        click.echo(f"  Target user: {config.github.target_username}")
        click.echo(f"  LLM model: {config.llm.model}")
        click.echo(f"  Timeout: {config.execution.timeout_seconds}s")
        sys.exit(0)
    except ConfigurationError as e:
        click.echo(click.style(f"Configuration invalid: {e}", fg="red"))
        sys.exit(1)
    except FileNotFoundError as e:
        click.echo(click.style(f"File not found: {e}", fg="red"))
        sys.exit(1)


@config.command()
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    default="config/config.yml",
    help="Path to configuration file.",
    show_default=True,
)
@click.option(
    "--raw",
    is_flag=True,
    default=False,
    help="Show raw YAML without processing.",
)
def show(config_path: Path, raw: bool) -> None:
    """Display current configuration."""
    configure_logging()

    try:
        if raw:
            with open(config_path, "r", encoding="utf-8") as f:
                click.echo(f.read())
        else:
            config = load_config(config_path)
            click.echo(yaml.dump(config.model_dump(), default_flow_style=False, sort_keys=False))
    except ConfigurationError as e:
        click.echo(click.style(f"Configuration error: {e}", fg="red"))
        sys.exit(1)
    except FileNotFoundError as e:
        click.echo(click.style(f"File not found: {e}", fg="red"))
        sys.exit(1)


@config.command()
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(path_type=Path),
    default="config/config.yml",
    help="Output path for configuration file.",
    show_default=True,
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite existing file.",
)
def init(output_path: Path, force: bool) -> None:
    """Create example configuration file."""
    configure_logging()

    if output_path.exists() and not force:
        click.echo(
            click.style(
                f"File already exists: {output_path}. Use --force to overwrite.",
                fg="yellow",
            )
        )
        sys.exit(1)

    example_config = """# PR Guardian Configuration
# See documentation for full configuration options

github:
  token_env: GITHUB_TOKEN
  target_username: your-username

repositories:
  - owner: your-org
    name: your-repo
    default_branch: main
    translation_patterns:
      - "*.properties"
      - "**/i18n/**/*.json"
      - "**/locales/**/*.yml"

feedback:
  repository: your-org/feedback-repo
  labels:
    - translation-feedback
    - automated
    - pr-guardian

execution:
  max_comments_per_pr: 50
  timeout_seconds: 1800
  schedule_cron: "0 2 * * *"

signing:
  method: web-flow
  # gpg_key_path: secrets/gpg_bot_key/bot_secret_key.asc
  # deploy_key_path: secrets/deploy_key/id_ed25519

llm:
  api_key_env: ANTHROPIC_API_KEY
  model: claude-3-haiku-20240307
  max_tokens: 1024
  confidence_threshold: 0.80
  human_review_threshold: 0.60

logging:
  level: INFO
"""

    # Create parent directories if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(example_config)

    click.echo(click.style(f"Configuration created: {output_path}", fg="green"))
    click.echo("\nNext steps:")
    click.echo("  1. Update github.target_username with your GitHub username")
    click.echo("  2. Configure repositories to monitor")
    click.echo("  3. Set GITHUB_TOKEN environment variable")
    click.echo("  4. Set ANTHROPIC_API_KEY environment variable")
    click.echo(f"  5. Run: pr-guardian config validate -c {output_path}")
