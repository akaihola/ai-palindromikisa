import argparse
import sys

from ai_palindromikisa.models import get_all_tested_models


def parse_cli_arguments() -> tuple[list[str], int | None]:
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
        "-l",
        "--limit",
        type=int,
        default=None,
        help="Limit the number of tasks to run per model",
    )
    args = parser.parse_args()

    # Handle models argument
    if args.models is None:
        # Default to gemini/gemini-2.0-flash if no models specified
        models = ["gemini/gemini-2.0-flash"]
    elif "ALL" in args.models:
        # Get all tested models
        models = get_all_tested_models()
        if models:
            print(f"Found {len(models)} previously tested models: {', '.join(models)}")
        else:
            print("No previously tested models found in benchmark_logs directory.")
            sys.exit(1)
    else:
        # Use explicitly specified models
        models = args.models
    return models, args.limit
