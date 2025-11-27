from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

from ruamel.yaml import YAML

if TYPE_CHECKING:
    from ai_palindromikisa.models import ModelConfig


def get_existing_logs(config: "ModelConfig", system_prompt: str) -> list:
    """Read all existing log files for the model configuration.

    Matches logs by the model file reference (which includes variation index).
    """
    # Get benchmark_logs directory path
    logs_dir = Path(__file__).parent.parent.parent / "benchmark_logs"

    if not logs_dir.exists():
        return []

    # The expected model file path reference in logs
    expected_model_path = f"models/{config.get_base_filename()}.yaml"
    # Also match by filename pattern (for backward compatibility and direct matching)
    expected_log_suffix = f"-{config.get_base_filename()}.yaml"

    existing_logs = []
    for log_file in logs_dir.glob("*.yaml"):
        try:
            yaml_obj = YAML()
            log_data = yaml_obj.load(log_file.read_text(encoding="utf-8"))

            # Check if system prompt matches
            if not (
                log_data.get("prompt_template", "")
                .strip()
                .startswith(system_prompt.strip())
            ):
                continue

            # Method 1: Check if log filename ends with expected suffix
            if log_file.name.endswith(expected_log_suffix):
                existing_logs.append(log_data)
                continue

            # Method 2: Check the model field in the log data
            model_field = log_data.get("model", "")
            if model_field == expected_model_path:
                existing_logs.append(log_data)
                continue

        except Exception as e:
            print(f"Warning: Could not read log file {log_file}: {e}")

    return existing_logs


def load_existing_log(log_path: Path):
    """Load existing log file or return empty structure if file doesn't exist."""
    if not log_path.exists():
        return None

    yaml_obj = YAML()
    return yaml_obj.load(log_path.read_text(encoding="utf-8"))


def save_log(log_path, log_data):
    """Save log data to file with proper formatting."""
    # Write to file with proper formatting for multi-line strings
    yaml_obj = YAML()
    yaml_obj.preserve_quotes = True
    yaml_obj.default_flow_style = False
    yaml_obj.allow_unicode = True
    yaml_obj.width = 4096  # Prevent line wrapping
    yaml_obj.indent(mapping=2, sequence=4, offset=2)

    # Configure ruamel.yaml to use literal block scalars for multi-line strings
    def represent_str(self, data):
        if "\n" in data and len(data.split("\n")) > 1:
            return self.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return self.represent_scalar("tag:yaml.org,2002:str", data)

    yaml_obj.representer.add_representer(str, represent_str)

    # Custom representer for floats to avoid scientific notation
    def represent_float(representer, value):
        if value != value:  # NaN
            return representer.represent_scalar("tag:yaml.org,2002:float", ".nan")
        elif value == float("inf"):
            return representer.represent_scalar("tag:yaml.org,2002:float", ".inf")
        elif value == float("-inf"):
            return representer.represent_scalar("tag:yaml.org,2002:float", "-.inf")
        else:
            # Format to avoid scientific notation, up to 10 decimal places
            formatted = f"{value:.10f}".rstrip("0").rstrip(".")
            if "." not in formatted:
                formatted += ".0"
            return representer.represent_scalar("tag:yaml.org,2002:float", formatted)

    yaml_obj.representer.add_representer(float, represent_float)

    # Convert to string and write using Path
    string_stream = StringIO()
    yaml_obj.dump(log_data, string_stream)
    log_path.write_text(string_stream.getvalue(), encoding="utf-8")


def get_log_path(config: "ModelConfig") -> Path:
    """Get the path to today's log file for the given model configuration."""
    # Generate filename with date and model config base filename
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_filename = f"benchmark_logs/{date_str}-{config.get_base_filename()}.yaml"

    # Create benchmark_logs directory if it doesn't exist
    log_path = Path(__file__).parent.parent.parent / log_filename
    log_path.parent.mkdir(parents=True, exist_ok=True)

    return log_path


def save_task_result(
    config: "ModelConfig",
    system_prompt: str,
    prompt: str,
    response_text: str,
    is_correct: bool,
    duration: float,
    timestamp: str,
    metadata: dict,
) -> Path:
    """Save a single task result to the log file."""
    log_path = get_log_path(config)

    # Generate model path reference
    model_path = f"models/{config.get_base_filename()}.yaml"

    # Load existing log or create new one
    existing_data = load_existing_log(log_path) or {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "model": model_path,
        "prompt_template": system_prompt,
        "tasks": [],
    }

    # Append the new task result
    existing_data["tasks"].append(
        {
            "timestamp": timestamp,
            "prompt": prompt,
            "answer": response_text,
            "is_correct": is_correct,
            "duration_seconds": round(duration, 2),
            "metadata": metadata,
        }
    )

    # Save the updated log
    save_log(log_path, existing_data)
    print(f"Task result saved to: {log_path}")
    return log_path


def get_completed_tasks(existing_logs) -> set[str]:
    """Get set of completed task prompts from existing logs."""
    completed_prompts = set()
    for log_data in existing_logs:
        for task in log_data.get("tasks", []):
            completed_prompts.add(task.get("prompt", ""))
    return completed_prompts
