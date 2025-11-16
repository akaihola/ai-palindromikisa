#!/usr/bin/env python3

import argparse
import re
import time
from datetime import datetime
from pathlib import Path

import llm
import yaml


def extract_palindrome(text):
    """Extract palindrome content from between <PALINDROMI> and </PALINDROMI> tags."""
    pattern = r"<PALINDROMI>(.*?)</PALINDROMI>"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


def normalize_text(text):
    """Normalize text by removing punctuation and converting to lowercase for comparison."""
    # Remove punctuation (commas, periods, exclamation marks, question marks, etc.)
    # and convert to lowercase for comparison
    import string

    # Remove punctuation
    text_no_punct = text.translate(str.maketrans("", "", string.punctuation))
    # Convert to lowercase and strip whitespace
    return text_no_punct.lower().strip()


def get_existing_logs(model_name, system_prompt):
    """Read all existing log files for the model variation."""
    # Get benchmark_logs directory path
    logs_dir = Path(__file__).parent.parent.parent / "benchmark_logs"

    if not logs_dir.exists():
        return []

    # Replace slashes with dashes in model name for filename matching
    model_filename = model_name.replace("/", "-")

    existing_logs = []
    for log_file in logs_dir.glob(f"*-{model_filename}.yaml"):
        try:
            log_data = yaml.safe_load(log_file.read_text(encoding="utf-8"))
            # Check if system prompt matches
            if (
                log_data.get("prompt_template", "")
                .strip()
                .startswith(system_prompt.strip())
            ):
                existing_logs.append(log_data)
        except Exception as e:
            print(f"Warning: Could not read log file {log_file}: {e}")

    return existing_logs


def get_completed_tasks(existing_logs):
    """Get set of completed task prompts from existing logs."""
    completed_prompts = set()
    for log_data in existing_logs:
        for task in log_data.get("tasks", []):
            completed_prompts.add(task.get("prompt", ""))
    return completed_prompts


def append_to_today_log(model_name, system_prompt, tasks, new_results):
    """Append new results to today's log file or create new one if doesn't exist."""
    # Generate filename with date and model name
    date_str = datetime.now().strftime("%Y-%m-%d")
    # Replace slashes with dashes in model name for filename
    model_filename = model_name.replace("/", "-")
    log_filename = f"benchmark_logs/{date_str}-{model_filename}.yaml"

    # Create benchmark_logs directory if it doesn't exist
    # From src/ai_palindromikisa/benchmark.py, go up 3 levels to reach project root
    log_path = Path(__file__).parent.parent.parent / log_filename
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate model path
    variation_index = 1  # TODO: Implement variation tracking
    model_path = f"models/{model_filename}-{variation_index}.yaml"

    # Create prompt template using actual system prompt
    # Preserve the original formatting from basic_tasks.yaml
    prompt_template = system_prompt.rstrip() + "\n\n{prompt}"

    # Check if today's log file exists
    if log_path.exists():
        # Read existing log
        existing_data = yaml.safe_load(log_path.read_text(encoding="utf-8"))
        existing_tasks = existing_data.get("tasks", [])
        # Append new results
        all_tasks = existing_tasks + new_results
    else:
        # Create new log
        all_tasks = new_results

    # Create log data structure
    log_data = {
        "date": date_str,
        "model": model_path,
        "prompt_template": prompt_template,
        "tasks": all_tasks,
    }

    # Write to file with proper formatting for multi-line strings
    # Use ruamel.yaml to preserve formatting and handle multi-line strings properly
    try:
        from ruamel.yaml import YAML

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

        with open(log_path, "w", encoding="utf-8") as f:
            yaml_obj.dump(log_data, f)
    except ImportError:
        # Fallback to PyYAML with custom dumper if ruamel.yaml is not available
        class MultilineStringDumper(yaml.SafeDumper):
            def represent_scalar(self, tag, value, style=None):
                # Use pipe syntax for multi-line strings
                if (
                    isinstance(value, str)
                    and "\n" in value
                    and len(value.split("\n")) > 1
                ):
                    style = "|"
                return super().represent_scalar(tag, value, style)

        log_path.write_text(
            yaml.dump(
                log_data,
                Dumper=MultilineStringDumper,
                default_flow_style=False,
                allow_unicode=True,
                width=4096,
            ),
            encoding="utf-8",
        )

    print(f"Log saved to: {log_path}")
    return log_path


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run palindrome benchmark tasks")
    parser.add_argument(
        "-m",
        "--model",
        default="gemini/gemini-2.0-flash",
        help="Model to use for the benchmark (default: gemini/gemini-2.0-flash)",
    )
    args = parser.parse_args()

    # Load the tasks from YAML using pathlib
    tasks_file = Path(__file__).parent / "benchmark_tasks/basic_tasks.yaml"

    # Use ruamel.yaml to preserve original formatting if available
    try:
        from ruamel.yaml import YAML

        yaml_obj = YAML()
        yaml_obj.preserve_quotes = True
        with open(tasks_file, "r", encoding="utf-8") as f:
            data = yaml_obj.load(f)
    except ImportError:
        # Fallback to PyYAML
        data = yaml.safe_load(tasks_file.read_text(encoding="utf-8"))

    system_prompt = data["system_prompt"]
    tasks = data["tasks"]

    # Read existing logs for this model variation
    existing_logs = get_existing_logs(args.model, system_prompt)
    completed_prompts = get_completed_tasks(existing_logs)

    print(f"Found {len(existing_logs)} existing log files for this model variation")
    print(f"Already completed {len(completed_prompts)} tasks\n")

    # Filter tasks to only run those not completed yet
    tasks_to_run = [task for task in tasks if task["prompt"] not in completed_prompts]

    if not tasks_to_run:
        print("All tasks have already been completed for this model variation!")
        return

    print(f"Running {len(tasks_to_run)} new tasks...\n")

    total_tasks_run = len(tasks_to_run)
    correct = 0
    new_results = []

    for task in tasks_to_run:
        prompt = task["prompt"]
        reference = task["reference"].strip().lower()
        task_id = task["id"]

        full_prompt = f"{system_prompt}\n\n{prompt}"

        # Time the task execution
        start_time = time.time()

        model = llm.get_model(args.model)

        print(f"Prompt: {prompt}")
        print(f"Reference: {reference}")

        response = model.prompt(full_prompt)
        response_text = extract_palindrome(response.text()).strip().lower()

        end_time = time.time()
        duration = end_time - start_time

        # Compare normalized text (ignoring punctuation)
        normalized_response = normalize_text(response_text)
        normalized_reference = normalize_text(reference)
        is_correct = normalized_response == normalized_reference
        if is_correct:
            correct += 1

        # Store result for logging - preserve original prompt formatting
        # Get the original task to preserve the exact prompt formatting
        original_task = next((t for t in tasks if t["id"] == task_id), task)
        task_result = {
            "prompt": original_task["prompt"],
            "answer": response_text,
            "is_correct": is_correct,
            "duration_seconds": round(duration, 2),
        }
        new_results.append(task_result)

        print(f"Response: {response_text}")
        print(f"Match: {'Yes' if is_correct else 'No'}")
        print(f"Duration: {duration:.2f}s\n")

    score = (correct / total_tasks_run) if total_tasks_run > 0 else 0
    print(f"New tasks score: {correct}/{total_tasks_run} correct ({score:.1f}%)")

    # Calculate overall score including existing tasks
    total_completed = len(completed_prompts) + total_tasks_run
    existing_correct = sum(
        1
        for log_data in existing_logs
        for task in log_data.get("tasks", [])
        if task.get("is_correct", False)
    )
    overall_correct = existing_correct + correct
    overall_score = (overall_correct / total_completed) if total_completed > 0 else 0
    print(
        f"Overall score: {overall_correct}/{total_completed} correct ({overall_score:.1f}%)"
    )

    # Append new results to today's log file
    append_to_today_log(args.model, system_prompt, tasks, new_results)


if __name__ == "__main__":
    main()
