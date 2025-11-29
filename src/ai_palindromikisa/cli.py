"""CLI module for ai-palindromikisa using Click."""

import sys

import click
from click_default_group import DefaultGroup

from ai_palindromikisa.models import ModelConfig, get_all_model_configs


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

    \b
    Commands:
      benchmark       Run palindrome benchmark tasks (default)
      stats           Extract and display statistics from benchmark logs
      tasks           Display task-level statistics across all models
      export-json     Export statistics as JSON for web visualization
      serve           Build and serve web interface locally
      update-pricing  Update pricing cache from LiteLLM repository
      migrate         Migrate files to new option-based naming convention
      delete-task     Delete task runs matching a search term
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
    from ai_palindromikisa.benchmark import run_benchmark_for_config
    from ai_palindromikisa.models import find_or_create_model_config
    from ai_palindromikisa.tasks import load_tasks

    # Handle models argument
    if not models:
        # Default to gemini/gemini-2.0-flash if no models specified
        model_configs = [ModelConfig(name="gemini/gemini-2.0-flash", options=options)]
    elif "ALL" in models:
        # Get all tested models from model files
        model_configs = get_all_model_configs()
        if model_configs:
            print(f"Found {len(model_configs)} model configurations")
        else:
            print("No model configuration files found in models directory.")
            sys.exit(1)
    else:
        # Use explicitly specified models with the provided options
        model_configs = [
            ModelConfig(name=model_name, options=options) for model_name in models
        ]

    # For configs from CLI (not ALL), find or create matching model files
    resolved_configs = []
    for config in model_configs:
        resolved_config = find_or_create_model_config(config.name, config.options)
        resolved_configs.append(resolved_config)

    config_names = [
        c.name + (f" {c.options}" if c.options else "") for c in resolved_configs
    ]
    print(f"Running benchmark for models: {', '.join(config_names)}\n")

    system_prompt, tasks = load_tasks()

    # Apply limit if specified
    if limit is not None:
        tasks = tasks[:limit]

    # Run benchmark for each model configuration
    for config in resolved_configs:
        run_benchmark_for_config(config, system_prompt, tasks)


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
    import json
    import sys

    from ai_palindromikisa.export_json import export_json

    data = export_json()
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
    print()  # Add trailing newline


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
    from pathlib import Path

    from livereload import Server

    from ai_palindromikisa.serve import build_site

    output_path = Path(output)

    print(f"Building site to {output_path}/...")
    build_site(output_path)
    print("Build complete.")

    if build_only:
        return

    # Create livereload server
    server = Server()

    # Watch benchmark_logs for changes and rebuild
    benchmark_logs = Path("benchmark_logs")
    if benchmark_logs.exists():
        server.watch(
            str(benchmark_logs / "*.yaml"),
            lambda: build_site(output_path),
        )

    # Watch web source files for changes
    web_dir = Path(__file__).parent / "web"
    server.watch(str(web_dir / "*"), lambda: build_site(output_path))

    print(f"Watching {benchmark_logs}/*.yaml and {web_dir}/* for changes...")
    print("Press Ctrl+C to stop.")

    # Serve the output directory with live reload
    server.serve(root=str(output_path), port=port, open_url_delay=None)


@cli.command(name="update-pricing")
def update_pricing_cmd() -> None:
    """Update pricing cache from LiteLLM repository."""
    from ai_palindromikisa.pricing_cache import update_pricing_cache

    if update_pricing_cache():
        print("Updated pricing data from LiteLLM repository")
    else:
        print("Failed to update pricing data from LiteLLM repository")
        sys.exit(1)


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
    from ai_palindromikisa.delete_task import delete_task_runs, find_matching_tasks

    print(f'Searching for tasks matching: "{search}"')
    print()

    # Find matching tasks from task definitions
    matching_tasks = find_matching_tasks(search)

    if not matching_tasks:
        print("No matching tasks found.")
        return

    print(f"Found {len(matching_tasks)} matching task(s):")
    for task in matching_tasks:
        print(f'  - Prompt: "{task["prompt"]}"')
        print(f'    Reference: "{task["reference"]}"')
    print()

    dry_run = not force
    if dry_run:
        print("DRY RUN - No changes will be made")
        print()

    print("Scanning log files...")
    matching_prompts = {task["prompt"] for task in matching_tasks}
    stats = delete_task_runs(matching_prompts, dry_run=dry_run)

    print()
    print("Summary:")
    print(f"  Files scanned: {stats['files_scanned']}")
    print(f"  Files {'to modify' if dry_run else 'modified'}: {stats['files_modified']}")
    print(f"  Tasks {'to delete' if dry_run else 'deleted'}: {stats['tasks_deleted']}")

    if dry_run and stats["tasks_deleted"] > 0:
        print()
        print("Run with --force to apply changes.")
