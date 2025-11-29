"""Export benchmark statistics as JSON for web visualization."""

from datetime import datetime, timezone

from ai_palindromikisa.extract_models import extract_models_from_logs
from ai_palindromikisa.plots import (
    FALLBACK_RICH_COLORS,
    MODEL_COLOR_PATTERNS,
    MODEL_MARKERS,
    _assign_markers,
)
from ai_palindromikisa.tasks_stats import load_task_stats


def _get_hex_color_for_model(model_name: str) -> str:
    """Get hex color for a model based on name patterns."""
    # Map rich colors to hex values
    rich_to_hex = {
        "dark_orange": "#d97757",
        "blue": "#3b82f6",
        "magenta": "#a855f7",
        "green": "#22c55e",
        "red": "#ef4444",
        "cyan": "#06b6d4",
        "bright_red": "#f87171",
        "bright_green": "#4ade80",
        "orange1": "#fb923c",
        "bright_blue": "#60a5fa",
        "bright_magenta": "#c084fc",
        "bright_cyan": "#22d3ee",
    }

    name_lower = model_name.lower()
    for pattern, (_, rich_color) in MODEL_COLOR_PATTERNS.items():
        if pattern in name_lower:
            return rich_to_hex.get(rich_color, "#888888")

    # Fallback - cycle through fallback colors
    return rich_to_hex.get(FALLBACK_RICH_COLORS[0], "#888888")


def _assign_hex_colors(model_names: list[str]) -> dict[str, str]:
    """Assign hex colors to all models."""
    rich_to_hex = {
        "dark_orange": "#d97757",
        "blue": "#3b82f6",
        "magenta": "#a855f7",
        "green": "#22c55e",
        "red": "#ef4444",
        "cyan": "#06b6d4",
        "bright_red": "#f87171",
        "bright_green": "#4ade80",
        "orange1": "#fb923c",
        "bright_blue": "#60a5fa",
        "bright_magenta": "#c084fc",
        "bright_cyan": "#22d3ee",
    }

    assignments: dict[str, str] = {}
    fallback_idx = 0

    for name in model_names:
        name_lower = name.lower()
        found = False
        for pattern, (_, rich_color) in MODEL_COLOR_PATTERNS.items():
            if pattern in name_lower:
                assignments[name] = rich_to_hex.get(rich_color, "#888888")
                found = True
                break
        if not found:
            idx = fallback_idx % len(FALLBACK_RICH_COLORS)
            assignments[name] = rich_to_hex.get(FALLBACK_RICH_COLORS[idx], "#888888")
            fallback_idx += 1

    return assignments


def export_json() -> dict:
    """Export all statistics as a JSON-serializable dictionary.

    Returns a dict with:
        - generated_at: ISO 8601 timestamp
        - models: list of model statistics
        - tasks: list of task statistics
        - totals: aggregate totals
        - chart_data: pre-computed data for scatterplots
    """
    # Get model statistics
    model_result = extract_models_from_logs()
    models_data = model_result["models"]
    total_cost = model_result["total_cost"]
    log_count = model_result["log_count"]

    # Get task statistics
    task_result = load_task_stats()
    tasks_data = task_result["tasks"]
    sorted_models = task_result["models"]

    # Assign markers and colors
    marker_map = _assign_markers(sorted_models)
    color_map = _assign_hex_colors(sorted_models)

    # Build models list sorted by accuracy
    models_list = []
    for model_name, stats in models_data.items():
        if stats["task_count"] == 0:
            continue
        accuracy = stats["correct_tasks"] / stats["task_count"]
        cost_per_task = stats["total_cost"] / stats["task_count"]
        time_per_task = stats["total_duration"] / stats["task_count"]
        sorted_dates = sorted(stats["dates"])

        # Cost per success: total_cost / correct_tasks (None if no successes)
        cost_per_success = (
            stats["total_cost"] / stats["correct_tasks"]
            if stats["correct_tasks"] > 0
            else None
        )

        models_list.append(
            {
                "name": model_name,
                "accuracy": accuracy,
                "correct": stats["correct_tasks"],
                "total": stats["task_count"],
                "cost_per_task": cost_per_task,
                "cost_per_success": cost_per_success,
                "time_per_task": time_per_task,
                "first_date": sorted_dates[0] if sorted_dates else None,
                "last_date": sorted_dates[-1] if sorted_dates else None,
                "marker": marker_map.get(model_name, "?"),
                "color": color_map.get(model_name, "#888888"),
            }
        )

    # Sort by accuracy descending
    models_list.sort(key=lambda m: m["accuracy"], reverse=True)

    # Build tasks list sorted by success rate
    tasks_list = []
    for prompt, data in tasks_data.items():
        if data["attempt_count"] == 0:
            continue
        success_rate = data["success_count"] / data["attempt_count"]
        avg_time = data["total_time"] / data["attempt_count"]
        avg_cost = data["total_cost"] / data["attempt_count"]

        tasks_list.append(
            {
                "prompt": prompt,
                "reference": data["reference"],
                "success_rate": success_rate,
                "avg_time": avg_time,
                "avg_cost": avg_cost,
                "model_results": {
                    model: result["correct"]
                    for model, result in data["model_results"].items()
                },
            }
        )

    # Sort by success rate descending
    tasks_list.sort(key=lambda t: t["success_rate"], reverse=True)

    # Build chart data for scatterplots
    # Top 5 models by accuracy for the time vs cost chart
    top5 = models_list[:5]

    chart_data = {
        "success_vs_cost": [
            {
                "name": m["name"],
                "x": m["cost_per_task"],
                "y": m["accuracy"] * 100,
                "marker": m["marker"],
                "color": m["color"],
            }
            for m in models_list
        ],
        "success_vs_time": [
            {
                "name": m["name"],
                "x": m["time_per_task"],
                "y": m["accuracy"] * 100,
                "marker": m["marker"],
                "color": m["color"],
            }
            for m in models_list
        ],
        "time_vs_cost_top5": [
            {
                "name": m["name"],
                "x": m["cost_per_task"],
                "y": m["time_per_task"],
                "marker": m["marker"],
                "color": m["color"],
            }
            for m in top5
        ],
        "success_vs_cost_per_success": [
            {
                "name": m["name"],
                "x": m["cost_per_success"],
                "y": m["accuracy"] * 100,
                "marker": m["marker"],
                "color": m["color"],
            }
            for m in models_list
            if m["cost_per_success"] is not None  # Exclude models with 0% success
        ],
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "models": models_list,
        "tasks": tasks_list,
        "sorted_model_names": sorted_models,
        "totals": {
            "cost": total_cost,
            "log_count": log_count,
        },
        "chart_data": chart_data,
    }
