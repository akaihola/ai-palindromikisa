"""Task statistics module for displaying benchmark task performance across models."""

from collections import defaultdict
from typing import cast

import yaml
from rich.console import Console
from rich.table import Table

from ai_palindromikisa.models import get_display_name_from_path
from ai_palindromikisa.paths import BENCHMARK_LOGS_DIR
from ai_palindromikisa.plots import (
    FALLBACK_RICH_COLORS,
    MODEL_COLOR_PATTERNS,
    MODEL_MARKERS,
    _assign_markers,
)
from ai_palindromikisa.tasks import load_tasks


def _extract_model_name(model_path: str) -> str:
    """Extract model display name from path using model config.

    Returns the llm library format with verbose options, e.g.:
        "openrouter/x-ai/grok-4: temperature 1.0"

    Falls back to cleaned filename if config can't be loaded.
    """
    return get_display_name_from_path(model_path)


def _get_rich_color_for_model(model_name: str) -> str:
    """Get rich color for a model based on name patterns."""
    name_lower = model_name.lower()
    for pattern, (_, rich_color) in MODEL_COLOR_PATTERNS.items():
        if pattern in name_lower:
            return rich_color
    return FALLBACK_RICH_COLORS[0]


def _get_marker_for_model(model_name: str) -> str | None:
    """Get predefined marker for a model name, or None if not found."""
    name_lower = model_name.lower()
    for pattern, marker in MODEL_MARKERS.items():
        if pattern in name_lower:
            return marker
    return None


def load_task_stats() -> dict:
    """Load and aggregate task statistics from benchmark logs.

    Returns a dict with:
        - tasks: dict mapping prompt -> task stats
        - models: list of model names sorted by success rate
        - marker_map: dict mapping model name to marker
        - color_map: dict mapping model name to rich color
    """
    if not BENCHMARK_LOGS_DIR.exists():
        return {"tasks": {}, "models": [], "marker_map": {}, "color_map": {}}

    # Load reference tasks to get correct answers
    _, reference_tasks = load_tasks()
    reference_map = {task["prompt"]: task["reference"] for task in reference_tasks}

    # Aggregate by task prompt
    tasks: dict[str, dict] = defaultdict(
        lambda: {
            "model_results": {},  # model_name -> {"correct": bool, "time": float, "cost": float}
            "total_time": 0.0,
            "total_cost": 0.0,
            "success_count": 0,
            "attempt_count": 0,
            "reference": "",
        }
    )

    # Track all models for marker/color assignment
    all_models: set[str] = set()
    model_success_counts: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))

    yaml_files = list(BENCHMARK_LOGS_DIR.glob("*.yaml"))

    for yaml_file in sorted(yaml_files):
        try:
            data = cast("dict", yaml.safe_load(yaml_file.read_text(encoding="utf-8")))
            model_path = data.get("model", "Unknown")
            model_name = _extract_model_name(cast("str", model_path))
            all_models.add(model_name)

            for task in data.get("tasks", []):
                prompt = task.get("prompt", "")
                is_correct = task.get("is_correct", False)
                duration = task.get("duration_seconds", 0)
                cost = task.get("metadata", {}).get("cost_usd", 0) or 0

                tasks[prompt]["model_results"][model_name] = {
                    "correct": is_correct,
                    "time": duration,
                    "cost": cost,
                }
                tasks[prompt]["total_time"] += duration
                tasks[prompt]["total_cost"] += cost
                tasks[prompt]["attempt_count"] += 1
                if is_correct:
                    tasks[prompt]["success_count"] += 1
                tasks[prompt]["reference"] = reference_map.get(prompt, "")

                # Track model success for sorting
                correct, total = model_success_counts[model_name]
                model_success_counts[model_name] = (
                    correct + (1 if is_correct else 0),
                    total + 1,
                )

        except Exception as e:
            print(f"Error processing {yaml_file.name}: {e}")

    # Sort models by success rate (descending)
    sorted_models = sorted(
        all_models,
        key=lambda m: (
            model_success_counts[m][0] / model_success_counts[m][1]
            if model_success_counts[m][1] > 0
            else 0
        ),
        reverse=True,
    )

    # Assign markers and colors
    marker_map = _assign_markers(sorted_models)
    color_map = {m: _get_rich_color_for_model(m) for m in sorted_models}

    return {
        "tasks": dict(tasks),
        "models": sorted_models,
        "marker_map": marker_map,
        "color_map": color_map,
    }


def _build_success_map(
    task_data: dict,
    models: list[str],
    marker_map: dict[str, str],
    color_map: dict[str, str],
) -> str:
    """Build a colored success map string for a task."""
    parts = []
    for model in models:
        result = task_data["model_results"].get(model)
        if result and result["correct"]:
            marker = marker_map[model]
            color = color_map[model]
            parts.append(f"[{color}]{marker}[/{color}]")
        else:
            parts.append(" ")
    return "".join(parts)


def display_task_stats() -> None:
    """Display task statistics table with success map and legend."""
    result = load_task_stats()
    tasks = result["tasks"]
    models = result["models"]
    marker_map = result["marker_map"]
    color_map = result["color_map"]

    if not tasks:
        print("No task statistics found.")
        return

    console = Console()

    # Calculate task metrics and sort by success percentage
    task_metrics = []
    for prompt, data in tasks.items():
        if data["attempt_count"] == 0:
            continue
        success_pct = (data["success_count"] / data["attempt_count"]) * 100
        avg_time = data["total_time"] / data["attempt_count"]
        avg_cost = data["total_cost"] / data["attempt_count"]
        task_metrics.append(
            (prompt, success_pct, avg_time, avg_cost, data["reference"], data)
        )

    # Sort by success percentage (descending)
    task_metrics.sort(key=lambda x: x[1], reverse=True)

    # Create table that expands to fill terminal width
    table = Table(
        title="Task Statistics (sorted by success %)", show_edge=False, expand=True
    )
    table.add_column("%", justify="right", no_wrap=True)
    table.add_column("Time", justify="right", no_wrap=True)
    table.add_column("¢/Task", justify="right", no_wrap=True)
    table.add_column("Models", justify="left", no_wrap=True)
    table.add_column("Answer", justify="left", overflow="ellipsis", ratio=1)
    table.add_column("Prompt", justify="left", overflow="ellipsis", ratio=2)

    for prompt, success_pct, avg_time, avg_cost, reference, data in task_metrics:
        success_map = _build_success_map(data, models, marker_map, color_map)
        avg_cost_cents = avg_cost * 100
        table.add_row(
            f"{success_pct:.0f}%",
            f"{avg_time:.1f}s",
            f"{avg_cost_cents:.2f}¢",
            success_map,
            reference,
            prompt,
        )

    console.print(table)

    # Print legend
    console.print()
    legend_table = Table(title="Model Legend", show_edge=False)
    legend_table.add_column("#", justify="right", no_wrap=True)
    legend_table.add_column("Model", justify="left")

    for model in models:
        marker = marker_map[model]
        color = color_map[model]
        legend_table.add_row(f"[{color}]{marker}[/{color}]", model)

    console.print(legend_table)
