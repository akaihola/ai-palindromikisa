#!/usr/bin/env python3
"""
Extract tested models from benchmark logs.
This script parses YAML files in the benchmark_logs directory to extract model information.
"""

import os
from datetime import datetime
from pathlib import Path

import yaml


def extract_models_from_logs(benchmark_dir="../../benchmark_logs"):
    """Extract model information from all YAML files in benchmark directory."""
    benchmark_path = Path(benchmark_dir)

    if not benchmark_path.exists():
        print(f"Error: Benchmark directory '{benchmark_dir}' not found.")
        return []

    models = []

    # Find all YAML files in the benchmark directory
    yaml_files = list(benchmark_path.glob("*.yaml"))

    if not yaml_files:
        print(f"No YAML files found in '{benchmark_dir}'.")
        return []

    print(f"Found {len(yaml_files)} benchmark log files:")
    print("-" * 50)

    for yaml_file in sorted(yaml_files):
        try:
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))

            # Extract model information
            model_info = {
                "filename": yaml_file.name,
                "date": data.get("date", "Unknown"),
                "model_path": data.get("model", "Unknown"),
                "task_count": len(data.get("tasks", [])),
                "correct_tasks": sum(
                    1 for task in data.get("tasks", []) if task.get("is_correct", False)
                ),
                "total_duration": sum(
                    task.get("duration_seconds", 0) for task in data.get("tasks", [])
                ),
            }

            # Extract model name from path (remove 'models/' prefix and version suffix)
            model_path = model_info["model_path"]
            if model_path.startswith("models/"):
                model_name = model_path[7:]  # Remove 'models/' prefix
                # Remove version suffix like '-1.yaml'
                if model_name.endswith(".yaml"):
                    model_name = model_name[:-5]
                    if "-1" in model_name:
                        model_name = model_name.rsplit("-1", 1)[0]
                model_info["model_name"] = model_name
            else:
                model_info["model_name"] = model_path

            models.append(model_info)

            # Print model info
            print(f"File: {model_info['filename']}")
            print(f"Date: {model_info['date']}")
            print(f"Model: {model_info['model_name']}")
            print(f"Model Path: {model_info['model_path']}")
            print(
                f"Tasks: {model_info['correct_tasks']}/{model_info['task_count']} correct"
            )
            print(f"Total Duration: {model_info['total_duration']:.2f}s")
            print("-" * 50)

        except Exception as e:
            print(f"Error processing {yaml_file.name}: {e}")
            print("-" * 50)

    return models


def main():
    """Main function to run the model extraction."""
    print("AI Palindromikisa - Model Extraction Tool")
    print("=" * 50)
    print(f"Running at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    models = extract_models_from_logs()

    if models:
        print(f"\nSummary:")
        print(f"Total models tested: {len(models)}")
        print(f"Test dates: {set(model['date'] for model in models)}")
        print(
            f"Model families: {set(model['model_name'].split('-')[0] for model in models)}"
        )

        # Sort models by performance (correct tasks)
        print(f"\nModels ranked by correct tasks:")
        for i, model in enumerate(
            sorted(models, key=lambda x: x["correct_tasks"], reverse=True), 1
        ):
            accuracy = (model["correct_tasks"] / model["task_count"]) * 100
            print(
                f"{i}. {model['model_name']}: {model['correct_tasks']}/{model['task_count']} ({accuracy:.1f}%)"
            )
    else:
        print("No models found or error occurred.")


if __name__ == "__main__":
    main()
