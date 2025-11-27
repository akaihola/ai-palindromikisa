#!/usr/bin/env python3
"""
AI-Palindromikisa - Main entry point for the ai-palindromikisa console script.

This module provides the main CLI interface with subcommands:
- benchmark: Run palindrome benchmark tasks
- stats: Extract and display statistics from benchmark logs
- tasks: Display task-level statistics across all models
- update-pricing: Update pricing cache from LiteLLM GitHub repository
- migrate: Migrate files from old naming convention to new option-based naming
"""

import sys

# Import the main functions from our modules
from .benchmark import main as benchmark_main
from .delete_task import main as delete_task_main
from .export_json import main as export_json_main
from .extract_models import main as extract_models_main
from .migrate import main as migrate_main
from .pricing_cache import update_pricing_cache
from .serve import main as serve_main
from .tasks_stats import main as tasks_stats_main


def main():
    """Main entry point for the ai-palindromikisa console script."""
    if len(sys.argv) < 2:
        print(
            "Usage: ai-palindromikisa "
            "{benchmark,stats,tasks,export-json,serve,update-pricing,migrate,delete-task} [options]"
        )
        print("  benchmark       Run palindrome benchmark tasks")
        print("  stats           Extract and display statistics from benchmark logs")
        print("  tasks           Display task-level statistics across all models")
        print("  export-json     Export statistics as JSON for web visualization")
        print("  serve           Build and serve web interface locally")
        print("  update-pricing  Update pricing cache from LiteLLM repository")
        print("  migrate         Migrate files to new option-based naming convention")
        print("  delete-task     Delete task runs matching a search term")
        print()
        print("For help with a specific command:")
        print("  ai-palindromikisa benchmark --help")
        print("  ai-palindromikisa stats --help")
        print("  ai-palindromikisa migrate --help")
        print("  ai-palindromikisa delete-task --help")
        sys.exit(1)

    command = sys.argv[1]

    # Handle help commands
    if command in ["-h", "--help", "help"]:
        print(
            "Usage: ai-palindromikisa "
            "{benchmark,stats,tasks,export-json,serve,update-pricing,migrate,delete-task} [options]"
        )
        print("  benchmark       Run palindrome benchmark tasks")
        print("  stats           Extract and display statistics from benchmark logs")
        print("  tasks           Display task-level statistics across all models")
        print("  export-json     Export statistics as JSON for web visualization")
        print("  serve           Build and serve web interface locally")
        print("  update-pricing  Update pricing cache from LiteLLM repository")
        print("  migrate         Migrate files to new option-based naming convention")
        print("  delete-task     Delete task runs matching a search term")
        print()
        print("For help with a specific command:")
        print("  ai-palindromikisa benchmark --help")
        print("  ai-palindromikisa stats --help")
        print("  ai-palindromikisa migrate --help")
        print("  ai-palindromikisa delete-task --help")
        sys.exit(0)

    # Remove the script name from sys.argv so subcommands can parse their own arguments
    sys.argv.pop(0)

    try:
        if command == "benchmark":
            benchmark_main()
        elif command == "stats":
            extract_models_main()
        elif command == "tasks":
            tasks_stats_main()
        elif command == "export-json":
            export_json_main()
        elif command == "serve":
            serve_main()
        elif command == "update-pricing":
            if update_pricing_cache():
                print("Updated pricing data from LiteLLM repository")
            else:
                print("Failed to update pricing data from LiteLLM repository")
                sys.exit(1)
        elif command == "migrate":
            migrate_main()
        elif command == "delete-task":
            delete_task_main()
        else:
            print(f"Unknown command: {command}")
            print(
                "Available commands: benchmark, stats, tasks, export-json, serve, "
                "update-pricing, migrate, delete-task"
            )
            print()
            print("For help with a specific command:")
            print("  ai-palindromikisa benchmark --help")
            print("  ai-palindromikisa stats --help")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
