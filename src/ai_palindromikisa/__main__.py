#!/usr/bin/env python3
"""
AI Palindromikisa - Main entry point for the ai-palindromikisa console script.

This module provides the main CLI interface with subcommands:
- benchmark: Run palindrome benchmark tasks
- stats: Extract and display statistics from benchmark logs
- update-pricing: Update pricing cache from LiteLLM GitHub repository
"""

import sys

# Import the main functions from our modules
from .benchmark import main as benchmark_main
from .extract_models import main as extract_models_main
from .pricing_cache import update_pricing_cache


def main():
    """Main entry point for the ai-palindromikisa console script."""
    if len(sys.argv) < 2:
        print("Usage: ai-palindromikisa {benchmark,stats,update-pricing} [options]")
        print("  benchmark       Run palindrome benchmark tasks")
        print("  stats           Extract and display statistics from benchmark logs")
        print("  update-pricing  Update pricing cache from LiteLLM repository")
        print()
        print("For help with a specific command:")
        print("  ai-palindromikisa benchmark --help")
        print("  ai-palindromikisa stats --help")
        sys.exit(1)

    command = sys.argv[1]

    # Handle help commands
    if command in ["-h", "--help", "help"]:
        print("Usage: ai-palindromikisa {benchmark,stats,update-pricing} [options]")
        print("  benchmark       Run palindrome benchmark tasks")
        print("  stats           Extract and display statistics from benchmark logs")
        print("  update-pricing  Update pricing cache from LiteLLM repository")
        print()
        print("For help with a specific command:")
        print("  ai-palindromikisa benchmark --help")
        print("  ai-palindromikisa stats --help")
        sys.exit(0)

    # Remove the script name from sys.argv so subcommands can parse their own arguments
    sys.argv.pop(0)

    try:
        if command == "benchmark":
            benchmark_main()
        elif command == "stats":
            extract_models_main()
        elif command == "update-pricing":
            if update_pricing_cache():
                print("Updated pricing data from LiteLLM repository")
            else:
                print("Failed to update pricing data from LiteLLM repository")
                sys.exit(1)
        else:
            print(f"Unknown command: {command}")
            print("Available commands: benchmark, stats, update-pricing")
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
