"""CLI entry point for PR Guardian."""

import click

from src import __version__

from .config import config
from .run import run


@click.group()
@click.version_option(version=__version__, prog_name="pr-guardian")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    PR Guardian - Automated translation PR management.

    Monitor translation PRs, process CodeRabbitAI comments,
    and automatically implement approved changes.
    """
    ctx.ensure_object(dict)


# Register subcommands
cli.add_command(run)
cli.add_command(config)


def main() -> None:
    """Main entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
