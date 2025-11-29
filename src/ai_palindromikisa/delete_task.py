"""Delete task runs from benchmark logs based on search term matching."""

from io import StringIO

from ruamel.yaml import YAML

from ai_palindromikisa.paths import BENCHMARK_LOGS_DIR
from ai_palindromikisa.tasks import load_tasks


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
    stats = {"files_scanned": 0, "files_modified": 0, "tasks_deleted": 0}

    if not BENCHMARK_LOGS_DIR.exists():
        return stats

    yaml_obj = YAML()
    yaml_obj.preserve_quotes = True
    yaml_obj.default_flow_style = False
    yaml_obj.allow_unicode = True
    yaml_obj.width = 4096

    for log_file in sorted(BENCHMARK_LOGS_DIR.glob("*.yaml")):
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


def delete_task_cli(search: str, force: bool) -> None:
    """CLI entry point to delete task runs from benchmark logs matching a search term.

    Args:
        search: Search term to match in task prompt or reference (case-insensitive).
        force: If True, actually delete. If False, dry-run only.
    """
    print(f'Searching for tasks matching: "{search}"')
    print()

    # Find matching tasks from task definitions
    matching_tasks = find_matching_tasks(search)

    if not matching_tasks:
        print("No matching tasks found.")
        return

    print(f"Found {len(matching_tasks)} matching task(s):")
    for task in matching_tasks:
        print(f'  - Prompt: "{task["prompt"]}"')
        print(f'    Reference: "{task["reference"]}"')
    print()

    dry_run = not force
    if dry_run:
        print("DRY RUN - No changes will be made")
        print()

    print("Scanning log files...")
    matching_prompts = {task["prompt"] for task in matching_tasks}
    stats = delete_task_runs(matching_prompts, dry_run=dry_run)

    print()
    print("Summary:")
    print(f"  Files scanned: {stats['files_scanned']}")
    print(f"  Files {'to modify' if dry_run else 'modified'}: {stats['files_modified']}")
    print(f"  Tasks {'to delete' if dry_run else 'deleted'}: {stats['tasks_deleted']}")

    if dry_run and stats["tasks_deleted"] > 0:
        print()
        print("Run with --force to apply changes.")
