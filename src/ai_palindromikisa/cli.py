import argparse
import sys

from ai_palindromikisa.models import ModelConfig, get_all_model_configs


def parse_cli_arguments() -> tuple[list[ModelConfig], int | None]:
    """Parse CLI arguments and return model configurations and limit.

    Returns:
        Tuple of (list of ModelConfig objects, optional limit)
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run palindrome benchmark tasks")
    parser.add_argument(
        "-m",
        "--model",
        action="append",
        dest="models",
        help=(
            "Model to use for the benchmark "
            "(can be specified multiple times, or use ALL for all tested models)"
        ),
    )
    parser.add_argument(
        "-o",
        nargs=2,
        action="append",
        metavar=("NAME", "VALUE"),
        dest="options",
        help="Option to pass to the model (e.g., -o temperature 0.3)",
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=None,
        help="Limit the number of tasks to run per model",
    )
    args = parser.parse_args()

    # Parse options into a dictionary
    options: dict[str, str | float | int | bool] = {}
    if args.options:
        for name, value in args.options:
            # Try to convert to appropriate type
            options[name] = _parse_option_value(value)

    # Handle models argument
    if args.models is None:
        # Default to gemini/gemini-2.0-flash if no models specified
        model_configs = [ModelConfig(name="gemini/gemini-2.0-flash", options=options)]
    elif "ALL" in args.models:
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
            ModelConfig(name=model_name, options=options) for model_name in args.models
        ]

    return model_configs, args.limit


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
