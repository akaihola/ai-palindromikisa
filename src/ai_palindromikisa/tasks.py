from pathlib import Path

from ruamel.yaml import YAML


def load_tasks() -> tuple[str, list]:
    # Load the tasks from YAML using pathlib
    tasks_file = Path(__file__).parent / "benchmark_tasks/basic_tasks.yaml"

    # Use ruamel.yaml to preserve original formatting
    yaml_obj = YAML()
    yaml_obj.preserve_quotes = True
    data = yaml_obj.load(tasks_file.read_text(encoding="utf-8"))

    return data["system_prompt"], data["tasks"]
