from ruamel.yaml import YAML

from ai_palindromikisa.paths import BASIC_TASKS_FILE


def load_tasks() -> tuple[str, list]:
    """Load benchmark tasks from the basic_tasks.yaml file."""
    # Use ruamel.yaml to preserve original formatting
    yaml_obj = YAML()
    yaml_obj.preserve_quotes = True
    data = yaml_obj.load(BASIC_TASKS_FILE.read_text(encoding="utf-8"))

    return data["system_prompt"], data["tasks"]
