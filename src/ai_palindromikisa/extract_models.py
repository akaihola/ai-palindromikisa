#!/usr/bin/env python3
"""
Extract tested models from benchmark logs.
This script parses YAML files in the benchmark_logs directory to extract model information.
"""

import argparse
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import cast

import yaml


def _extract_model_name(model_path: str) -> str:
    """Extract model name from path (remove 'models/' prefix and version suffix)."""
    if model_path.startswith("models/"):
        model_name = model_path[7:]  # Remove 'models/' prefix
        # Remove version suffix like '-1.yaml'
        if model_name.endswith(".yaml"):
            model_name = model_name[:-5]
            if "-1" in model_name:
                model_name = model_name.rsplit("-1", 1)[0]
        return model_name
    return model_path


def extract_models_from_logs(benchmark_dir: str = "../../benchmark_logs") -> dict:
    """Extract model information from all YAML files in benchmark directory.

    Returns a dict with:
        - models: dict mapping model_name to aggregated stats
        - total_cost: total cost across all tasks
        - log_count: number of log files processed
    """
    # Get the script's directory and make benchmark_logs path relative to it
    script_dir = Path(__file__).parent.parent.parent
    benchmark_path = script_dir / "benchmark_logs"

    if not benchmark_path.exists():
        print(f"Error: Benchmark directory '{benchmark_dir}' not found.")
        return {"models": {}, "total_cost": 0.0, "log_count": 0}

    # Aggregate by unique model name
    models: dict[str, dict] = defaultdict(
        lambda: {
            "task_count": 0,
            "correct_tasks": 0,
            "total_duration": 0.0,
            "total_cost": 0.0,
            "dates": set(),
            "filenames": [],
        }
    )
    total_cost = 0.0

    # Find all YAML files in the benchmark directory
    yaml_files = list(benchmark_path.glob("*.yaml"))

    if not yaml_files:
        print(f"No YAML files found in '{benchmark_dir}'.")
        return {"models": {}, "total_cost": 0.0, "log_count": 0}

    for yaml_file in sorted(yaml_files):
        try:
            data = cast("dict", yaml.safe_load(yaml_file.read_text(encoding="utf-8")))
            tasks = data.get("tasks", [])

            model_path = data.get("model", "Unknown")
            model_name = _extract_model_name(cast("str", model_path))
            date = data.get("date", "Unknown")

            # Calculate costs from task metadata
            file_cost = sum(
                task.get("metadata", {}).get("cost_usd", 0) or 0 for task in tasks
            )

            # Aggregate stats for this model
            models[model_name]["task_count"] += len(tasks)
            models[model_name]["correct_tasks"] += sum(
                1 for task in tasks if task.get("is_correct", False)
            )
            models[model_name]["total_duration"] += sum(
                task.get("duration_seconds", 0) for task in tasks
            )
            models[model_name]["total_cost"] += file_cost
            models[model_name]["dates"].add(date)
            models[model_name]["filenames"].append(yaml_file.name)

            total_cost += file_cost

        except Exception as e:
            print(f"Error processing {yaml_file.name}: {e}")

    return {
        "models": dict(models),
        "total_cost": total_cost,
        "log_count": len(yaml_files),
    }


def main() -> None:
    """Main function to run the model extraction."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog="ai-palindromikisa stats",
        description="Extract and display statistics from benchmark logs",
    )
    parser.parse_args()

    print("AI Palindromikisa - Model Statistics")
    print("=" * 50)
    print(f"Running at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    result = extract_models_from_logs()
    models = result["models"]
    total_cost = result["total_cost"]
    log_count = result["log_count"]

    if models:
        print(f"Found {log_count} benchmark log files for {len(models)} unique models")
        print("-" * 50)

        # Sort models by performance (correct tasks ratio)
        sorted_models = sorted(
            models.items(),
            key=lambda x: (
                x[1]["correct_tasks"] / x[1]["task_count"]
                if x[1]["task_count"] > 0
                else 0
            ),
            reverse=True,
        )

        print("\nModels ranked by accuracy:")
        print()
        for i, (model_name, stats) in enumerate(sorted_models, 1):
            accuracy = (
                (stats["correct_tasks"] / stats["task_count"]) * 100
                if stats["task_count"] > 0
                else 0
            )
            avg_cost = (
                stats["total_cost"] / stats["task_count"]
                if stats["task_count"] > 0
                else 0
            )
            dates_str = ", ".join(sorted(stats["dates"]))

            print(
                f"{i:2}. {model_name}: "
                f"{stats['correct_tasks']}/{stats['task_count']} ({accuracy:.1f}%) "
                f"- ${stats['total_cost']:.4f} total, ${avg_cost:.6f}/task"
            )
            print(f"    Dates: {dates_str}")

        print()
        print("-" * 50)
        print(f"Total cost across all logged tasks: ${total_cost:.4f}")
    else:
        print("No models found or error occurred.")


if __name__ == "__main__":
    main()
