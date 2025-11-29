"""CLI module for ai-palindromikisa using Click."""

import click
from click_default_group import DefaultGroup


def _parse_option_value(value: str) -> str | float | int | bool:
    """Parse an option value string to the appropriate type."""
    # Try boolean
    if value.lower() in ("true", "on", "yes"):
        return True
    if value.lower() in ("false", "off", "no"):
        return False

    # Try integer
    try:
        return int(value)
    except ValueError:
        pass

    # Try float
    try:
        return float(value)
    except ValueError:
        pass

    # Return as string
    return value


def option_callback(
    ctx: click.Context, param: click.Parameter, value: tuple[tuple[str, str], ...]
) -> dict[str, str | float | int | bool]:
    """Callback to parse option tuples into a dictionary."""
    options: dict[str, str | float | int | bool] = {}
    for name, val in value:
        options[name] = _parse_option_value(val)
    return options


@click.group(
    cls=DefaultGroup,
    default="benchmark",
    default_if_no_args=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option()
def cli() -> None:
    """AI-Palindromikisa - Benchmark LLMs on Finnish palindrome generation.

    Documentation: https://github.com/akaihola/ai-palindromikisa
    """


@cli.command(name="benchmark")
@click.option(
    "-m",
    "--model",
    "models",
    multiple=True,
    help="Model to use (can specify multiple times, or use ALL for all tested models)",
)
@click.option(
    "-o",
    "--option",
    "options",
    nargs=2,
    multiple=True,
    metavar="NAME VALUE",
    callback=option_callback,
    help="Option to pass to the model (e.g., -o temperature 0.3)",
)
@click.option(
    "-l",
    "--limit",
    type=int,
    default=None,
    help="Limit the number of tasks to run per model",
)
def benchmark_cmd(
    models: tuple[str, ...],
    options: dict[str, str | float | int | bool],
    limit: int | None,
) -> None:
    """Run palindrome benchmark tasks."""
    from ai_palindromikisa.benchmark import run_benchmark

    run_benchmark(models, options, limit)


@cli.command(name="stats")
def stats_cmd() -> None:
    """Extract and display statistics from benchmark logs."""
    from ai_palindromikisa.extract_models import display_stats

    display_stats()


@cli.command(name="tasks")
def tasks_cmd() -> None:
    """Display task-level statistics across all models."""
    from ai_palindromikisa.tasks_stats import display_task_stats

    display_task_stats()


@cli.command(name="export-json")
def export_json_cmd() -> None:
    """Export statistics as JSON for web visualization."""
    from ai_palindromikisa.export_json import export_json_to_stdout

    export_json_to_stdout()


@cli.command(name="serve")
@click.option(
    "-p", "--port", type=int, default=8000, help="Port to serve on (default: 8000)"
)
@click.option("--build-only", is_flag=True, help="Only build, don't start server")
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    default="gh-pages",
    help="Output directory (default: gh-pages)",
)
def serve_cmd(port: int, build_only: bool, output: str) -> None:
    """Build and serve the web interface locally with live reload."""
    from ai_palindromikisa.serve import serve_site

    serve_site(port, build_only, output)


@cli.command(name="update-pricing")
def update_pricing_cmd() -> None:
    """Update pricing cache from LiteLLM repository."""
    from ai_palindromikisa.pricing_cache import update_pricing_cli

    update_pricing_cli()


@cli.command(name="migrate")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without making changes",
)
def migrate_cmd(dry_run: bool) -> None:
    """Migrate files to new option-based naming convention."""
    from ai_palindromikisa.migrate import migrate_files

    migrate_files(dry_run=dry_run)


@cli.command(name="delete-task")
@click.option(
    "-s",
    "--search",
    required=True,
    help="Search term to match in task prompt or reference (case-insensitive)",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Actually delete (default is dry-run)",
)
def delete_task_cmd(search: str, force: bool) -> None:
    """Delete task runs from benchmark logs matching a search term."""
    from ai_palindromikisa.delete_task import delete_task_cli

    delete_task_cli(search, force)
