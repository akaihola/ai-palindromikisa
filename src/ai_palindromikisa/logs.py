from datetime import datetime
from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML


def get_existing_logs(model_name: str, system_prompt: str) -> list:
    """Read all existing log files for the model variation."""
    # Get benchmark_logs directory path
    logs_dir = Path(__file__).parent.parent.parent / "benchmark_logs"

    if not logs_dir.exists():
        return []

    # Replace slashes with dashes in model name for filename matching
    model_filename = model_name.replace("/", "-")

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

            # Check if this log file matches our model
            # Method 1: Check filename pattern
            if f"-{model_filename}.yaml" in log_file.name:
                existing_logs.append(log_data)
                continue

            # Method 2: Check the model field in the log data
            # Extract model from log_data.model field and normalize it
            model_field = log_data.get("model", "")
            if model_field:
                # Remove "models/" prefix and "-1.yaml" suffix
                clean_model = model_field.replace("models/", "").replace("-1.yaml", "")
                # Convert dashes to slashes for comparison
                clean_model = clean_model.replace("-", "/")

                # Check if the cleaned model matches our target model
                if clean_model == model_name:
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

    # Convert to string and write using Path
    string_stream = StringIO()
    yaml_obj.dump(log_data, string_stream)
    log_path.write_text(string_stream.getvalue(), encoding="utf-8")


def get_log_path(model_name: str) -> Path:
    """Get the path to today's log file for the given model."""
    # Generate filename with date and model name
    date_str = datetime.now().strftime("%Y-%m-%d")
    # Replace slashes with dashes in model name for filename
    model_filename = model_name.replace("/", "-")
    log_filename = f"benchmark_logs/{date_str}-{model_filename}.yaml"

    # Create benchmark_logs directory if it doesn't exist
    # From src/ai_palindromikisa/benchmark.py, go up 3 levels to reach project root
    log_path = Path(__file__).parent.parent.parent / log_filename
    log_path.parent.mkdir(parents=True, exist_ok=True)

    return log_path


def save_task_result(
    model_name: str,
    system_prompt: str,
    prompt: str,
    response_text: str,
    is_correct: bool,
    duration: float,
    timestamp: str,
    metadata: dict,
) -> Path:
    """Save a single task result to the log file."""
    log_path = get_log_path(model_name)

    # Generate model path
    model_filename = model_name.replace("/", "-")
    variation_index = 1  # TODO: Implement variation tracking
    model_path = f"models/{model_filename}-{variation_index}.yaml"

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
