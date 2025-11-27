"""Console scatterplots for model statistics using plotext."""

import os
import string

import plotext as plt
from rich.console import Console
from rich.table import Table

# Model color mapping based on provider/name patterns
# Maps pattern (matched case-insensitively) to (plotext_color, rich_color)
MODEL_COLOR_PATTERNS: dict[str, tuple[str, str]] = {
    "anthropic": ("orange", "dark_orange"),  # closest to rgb(217 119 87)
    "gemini": ("blue", "blue"),
    "gpt": ("magenta", "magenta"),
    "grok": ("green", "green"),
}

# Fallback colors for models not matching any pattern
FALLBACK_PLOTEXT_COLORS = [
    "red",
    "cyan",
    "red+",
    "green+",
    "orange+",
    "blue+",
    "magenta+",
    "cyan+",
]

FALLBACK_RICH_COLORS = [
    "red",
    "cyan",
    "bright_red",
    "bright_green",
    "orange1",
    "bright_blue",
    "bright_magenta",
    "bright_cyan",
]

# Plot dimensions: min 60x20, max 120x40, aspect ratio 3:1 (width:height)
MIN_WIDTH = 60
MIN_HEIGHT = 20
MAX_WIDTH = 120
MAX_HEIGHT = 40
ASPECT_RATIO = 3.0  # width / height

# Known model markers - patterns matched against model name (case-insensitive)
MODEL_MARKERS: dict[str, str] = {
    "haiku": "H",
    "sonnet": "S",
    "3-opus": "o",
    "opus-4.5": "O",
    "gemini-3": "3",
    "gemini-2.0-flash": "f",
    "gemini-2.5-flash": "F",
    "gemini-2.5-pro": "2",
    "gpt-4o-mini": "g",
    "mistral": "m",
    "kimi-k2": "k",
    "gpt-5": "G",
    "grok-4": "4",
    "glm-4": "z",
}

# Fallback markers for unknown models (excluding reserved ones)
RESERVED_MARKERS = set(MODEL_MARKERS.values())
FALLBACK_MARKERS = [
    c
    for c in list(string.digits[1:])
    + list(string.ascii_lowercase)
    + list(string.ascii_uppercase)
    if c not in RESERVED_MARKERS
]


def _get_marker_for_model(model_name: str) -> str | None:
    """Get predefined marker for a model name, or None if not found."""
    name_lower = model_name.lower()
    for pattern, marker in MODEL_MARKERS.items():
        if pattern in name_lower:
            return marker
    return None


def _assign_markers(model_names: list[str]) -> dict[str, str]:
    """Assign markers to all models, using predefined ones where available."""
    assignments: dict[str, str] = {}
    used_markers: set[str] = set()
    fallback_idx = 0

    for name in model_names:
        marker = _get_marker_for_model(name)
        if marker and marker not in used_markers:
            assignments[name] = marker
            used_markers.add(marker)
        else:
            # Find next available fallback marker
            while fallback_idx < len(FALLBACK_MARKERS):
                fallback = FALLBACK_MARKERS[fallback_idx]
                fallback_idx += 1
                if fallback not in used_markers:
                    assignments[name] = fallback
                    used_markers.add(fallback)
                    break
            else:
                # Exhausted fallbacks, use ?
                assignments[name] = "?"

    return assignments


def _get_plot_size() -> tuple[int, int]:
    """Calculate plot size based on terminal size, respecting min/max and aspect ratio."""
    try:
        term_width, term_height = os.get_terminal_size()
    except OSError:
        return MIN_WIDTH, MIN_HEIGHT

    # Leave some margin for borders and labels
    available_width = min(term_width - 10, MAX_WIDTH)
    available_height = min(term_height - 10, MAX_HEIGHT)

    # Calculate dimensions maintaining aspect ratio
    width_from_height = int(available_height * ASPECT_RATIO)
    height_from_width = int(available_width / ASPECT_RATIO)

    if width_from_height <= available_width:
        width = width_from_height
        height = available_height
    else:
        width = available_width
        height = height_from_width

    # Ensure minimums
    width = max(width, MIN_WIDTH)
    height = max(height, MIN_HEIGHT)

    return width, height


def _compute_model_metrics(
    models: dict[str, dict],
) -> list[tuple[str, float, float, float]]:
    """Compute metrics for each model.

    Returns list of (name, success_pct, cost_per_task, time_per_task) tuples.
    """
    metrics = []
    for name, stats in models.items():
        if stats["task_count"] == 0:
            continue
        success_pct = (stats["correct_tasks"] / stats["task_count"]) * 100
        cost_per_task = stats["total_cost"] / stats["task_count"]
        time_per_task = stats["total_duration"] / stats["task_count"]
        metrics.append((name, success_pct, cost_per_task, time_per_task))
    return metrics


def _get_color_for_model(model_name: str) -> tuple[str, str]:
    """Get (plotext_color, rich_color) for a model based on name patterns."""
    name_lower = model_name.lower()
    for pattern, colors in MODEL_COLOR_PATTERNS.items():
        if pattern in name_lower:
            return colors
    return None, None


def _assign_colors(
    model_names: list[str],
) -> dict[str, tuple[str, str]]:
    """Assign colors to all models based on name patterns, with fallbacks."""
    assignments: dict[str, tuple[str, str]] = {}
    fallback_idx = 0

    for name in model_names:
        plotext_color, rich_color = _get_color_for_model(name)
        if plotext_color:
            assignments[name] = (plotext_color, rich_color)
        else:
            # Use fallback color
            idx = fallback_idx % len(FALLBACK_PLOTEXT_COLORS)
            assignments[name] = (
                FALLBACK_PLOTEXT_COLORS[idx],
                FALLBACK_RICH_COLORS[idx],
            )
            fallback_idx += 1

    return assignments


def _print_legend(
    metrics: list[tuple[str, float, float, float]],
    marker_map: dict[str, str],
    color_map: dict[str, tuple[str, str]],
    title: str,
) -> None:
    """Print a legend table mapping colored markers to model names."""
    console = Console()
    table = Table(title=title, show_edge=False)
    table.add_column("#", justify="right")
    table.add_column("Model", justify="left")
    for name, _, _, _ in metrics:
        marker = marker_map[name]
        _, rich_color = color_map[name]
        table.add_row(f"[{rich_color}]{marker}[/{rich_color}]", name)
    console.print(table)


def _setup_plot() -> None:
    """Configure common plot settings."""
    plt.clear_figure()
    plt.clear_color()
    width, height = _get_plot_size()
    plt.plotsize(width, height)
    plt.theme("clear")  # No built-in legend


def plot_success_vs_cost(
    metrics: list[tuple[str, float, float, float]],
    marker_map: dict[str, str],
    color_map: dict[str, tuple[str, str]],
) -> None:
    """Plot Success % vs ¢/Task for all models."""
    _setup_plot()
    plt.title("Success % vs ¢/Task (all models)")
    plt.xlabel("¢/Task")
    plt.ylabel("Success %")

    successes = [m[1] for m in metrics]

    # Plot each point with its marker (convert cost to cents)
    for i, (name, _, cost, _) in enumerate(metrics):
        y = successes[i]
        x = cost * 100  # Convert to cents
        marker = marker_map[name]
        plotext_color, _ = color_map[name]
        plt.scatter([x], [y], marker=marker, color=plotext_color)

    plt.show()
    _print_legend(metrics, marker_map, color_map, "Legend")


def plot_success_vs_time(
    metrics: list[tuple[str, float, float, float]],
    marker_map: dict[str, str],
    color_map: dict[str, tuple[str, str]],
) -> None:
    """Plot Success % vs Time/Task for all models."""
    _setup_plot()
    plt.title("Success % vs Time/Task (all models)")
    plt.xlabel("Time/Task (seconds)")
    plt.ylabel("Success %")

    successes = [m[1] for m in metrics]

    for i, (name, _, _, x) in enumerate(metrics):
        y = successes[i]
        marker = marker_map[name]
        plotext_color, _ = color_map[name]
        plt.scatter([x], [y], marker=marker, color=plotext_color)

    plt.show()
    _print_legend(metrics, marker_map, color_map, "Legend")


def plot_time_vs_cost_top5(
    metrics: list[tuple[str, float, float, float]],
    marker_map: dict[str, str],
    color_map: dict[str, tuple[str, str]],
) -> None:
    """Plot Time/Task vs ¢/Task for top 5 models by success rate."""
    # Sort by success rate and take top 5
    sorted_metrics = sorted(metrics, key=lambda m: m[1], reverse=True)[:5]

    _setup_plot()
    plt.title("Time/Task vs ¢/Task (top 5 by success)")
    plt.xlabel("¢/Task")
    plt.ylabel("Time/Task (s)")

    for name, _, cost, time in sorted_metrics:
        marker = marker_map[name]
        plotext_color, _ = color_map[name]
        plt.scatter([cost * 100], [time], marker=marker, color=plotext_color)

    plt.show()
    _print_legend(sorted_metrics, marker_map, color_map, "Legend (top 5)")


def show_all_plots(models: dict[str, dict]) -> None:
    """Display all three scatterplots."""
    metrics = _compute_model_metrics(models)
    model_names = [m[0] for m in metrics]
    marker_map = _assign_markers(model_names)
    color_map = _assign_colors(model_names)

    plot_success_vs_cost(metrics, marker_map, color_map)
    print()
    plot_success_vs_time(metrics, marker_map, color_map)
    print()
    plot_time_vs_cost_top5(metrics, marker_map, color_map)
