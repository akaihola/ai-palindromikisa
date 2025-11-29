"""Delete task runs from benchmark logs based on search term matching."""

from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML

from ai_palindromikisa.tasks import load_tasks


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def find_matching_tasks(search_term: str) -> list[dict]:
    """Find tasks where search term appears in prompt or reference.

    Args:
        search_term: Substring to search for (case-insensitive)

    Returns:
        List of matching task dicts with 'prompt' and 'reference' keys
    """
    _, tasks = load_tasks()
    search_lower = search_term.lower()

    matching = []
    for task in tasks:
        prompt = task.get("prompt", "")
        reference = task.get("reference", "")
        if search_lower in prompt.lower() or search_lower in reference.lower():
            matching.append({"prompt": prompt, "reference": reference})

    return matching


def delete_task_runs(
    matching_prompts: set[str], dry_run: bool = True
) -> dict[str, int]:
    """Delete task runs from all log files where prompt matches.

    Args:
        matching_prompts: Set of task prompts to delete
        dry_run: If True, only report what would be deleted

    Returns:
        Statistics dict with files_scanned, files_modified, tasks_deleted
    """
    project_root = get_project_root()
    logs_dir = project_root / "benchmark_logs"

    stats = {"files_scanned": 0, "files_modified": 0, "tasks_deleted": 0}

    if not logs_dir.exists():
        return stats

    yaml_obj = YAML()
    yaml_obj.preserve_quotes = True
    yaml_obj.default_flow_style = False
    yaml_obj.allow_unicode = True
    yaml_obj.width = 4096

    for log_file in sorted(logs_dir.glob("*.yaml")):
        stats["files_scanned"] += 1

        try:
            log_data = yaml_obj.load(log_file.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  ERROR reading {log_file.name}: {e}")
            continue

        tasks = log_data.get("tasks", [])
        original_count = len(tasks)

        # Filter out matching tasks
        remaining_tasks = [
            task for task in tasks if task.get("prompt", "") not in matching_prompts
        ]
        deleted_count = original_count - len(remaining_tasks)

        if deleted_count > 0:
            action = "would delete" if dry_run else "deleted"
            print(f"  {log_file.name}: {deleted_count} task(s) {action}")
            stats["files_modified"] += 1
            stats["tasks_deleted"] += deleted_count

            if not dry_run:
                log_data["tasks"] = remaining_tasks
                string_stream = StringIO()
                yaml_obj.dump(log_data, string_stream)
                log_file.write_text(string_stream.getvalue(), encoding="utf-8")

    return stats
