#!/usr/bin/env python3

import argparse
import re
import time
from datetime import datetime
from io import StringIO
from pathlib import Path

import llm
from ruamel.yaml import YAML


def get_all_tested_models():
    """Extract model IDs from model configuration files in the models directory."""
    models_dir = Path(__file__).parent.parent.parent / "models"

    if not models_dir.exists():
        print(f"Warning: Models directory '{models_dir}' not found.")
        print("Please create the models directory and add model configuration files.")
        return []

    models = set()
    model_files_found = 0

    for model_file in models_dir.glob("*.yaml"):
        model_files_found += 1
        try:
            yaml_obj = YAML()
            model_data = yaml_obj.load(model_file.read_text(encoding="utf-8"))
            # Extract the model name from the name field
            model_name = model_data.get("name", "")
            if model_name:
                models.add(model_name)
                print(f"Found model: {model_name} (from {model_file.name})")
            else:
                print(f"Warning: No 'name' field found in {model_file.name}")
        except Exception as e:
            print(f"Warning: Could not read model file {model_file.name}: {e}")

    if model_files_found == 0:
        print("No model configuration files found in models directory.")
    elif len(models) == 0:
        print(
            f"Found {model_files_found} model files but none had valid 'name' fields."
        )

    return sorted(list(models))


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

                # Special case: handle gemini/gemini-2.0-flash vs gemini/2.0-flash
                if (
                    model_name == "gemini/gemini-2.0-flash"
                    and clean_model == "gemini/2.0-flash"
                ):
                    existing_logs.append(log_data)
                    continue
                if (
                    model_name == "gemini/2.0-flash"
                    and clean_model == "gemini/gemini-2.0-flash"
                ):
                    existing_logs.append(log_data)
                    continue

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


def ensure_model_metadata_exists(model_name):
    """Ensure the model metadata file exists in the models directory.

    Creates the file if it doesn't exist, regardless of whether tasks will be executed.

    Args:
        model_name: The model name (e.g., "gemini/gemini-2.0-flash")

    Returns:
        Path to the model metadata file
    """
    # Get models directory path
    models_dir = Path(__file__).parent.parent.parent / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    # Convert model name to filename format (replace slashes with dashes)
    model_filename = model_name.replace("/", "-")
    model_file_path = models_dir / f"{model_filename}-1.yaml"

    # If the file already exists, return its path
    if model_file_path.exists():
        return model_file_path

    # Create the model metadata file with basic structure
    model_metadata = {"name": model_name}

    # Write the metadata file
    yaml_obj = YAML()
    yaml_obj.preserve_quotes = True
    yaml_obj.default_flow_style = False
    yaml_obj.allow_unicode = True

    # Convert to string and write using Path
    string_stream = StringIO()
    yaml_obj.dump(model_metadata, string_stream)
    model_file_path.write_text(string_stream.getvalue(), encoding="utf-8")

    print(f"Created model metadata file: {model_file_path}")
    return model_file_path


def get_log_path(model_name):
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


def load_existing_log(log_path):
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


def append_to_today_log(model_name, system_prompt, tasks, new_results):
    """Append new results to today's log file or create new one if doesn't exist."""
    log_path = get_log_path(model_name)

    # Generate model path
    model_filename = model_name.replace("/", "-")
    variation_index = 1  # TODO: Implement variation tracking
    model_path = f"models/{model_filename}-{variation_index}.yaml"

    # Create prompt template using actual system prompt
    # Preserve the original formatting from basic_tasks.yaml
    prompt_template = system_prompt.rstrip() + "\n\n{prompt}"

    # Check if today's log file exists
    existing_data = load_existing_log(log_path)
    if existing_data:
        existing_tasks = existing_data.get("tasks", [])
        # Append new results
        all_tasks = existing_tasks + new_results
    else:
        # Create new log
        all_tasks = new_results
        existing_data = {}

    # Create log data structure
    log_data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "model": model_path,
        "prompt_template": prompt_template,
        "tasks": all_tasks,
    }

    # Save the log
    save_log(log_path, log_data)
    print(f"Log saved to: {log_path}")
    return log_path


def save_task_result(model_name, system_prompt, task_result):
    """Save a single task result to the log file."""
    log_path = get_log_path(model_name)

    # Generate model path
    model_filename = model_name.replace("/", "-")
    variation_index = 1  # TODO: Implement variation tracking
    model_path = f"models/{model_filename}-{variation_index}.yaml"

    # Create prompt template using actual system prompt
    prompt_template = system_prompt.rstrip() + "\n\n{prompt}"

    # Load existing log or create new one
    existing_data = load_existing_log(log_path)
    if existing_data:
        existing_tasks = existing_data.get("tasks", [])
    else:
        existing_tasks = []
        existing_data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "model": model_path,
            "prompt_template": prompt_template,
            "tasks": [],
        }

    # Append the new task result
    existing_data["tasks"].append(task_result)

    # Save the updated log
    save_log(log_path, existing_data)
    print(f"Task result saved to: {log_path}")
    return log_path


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run palindrome benchmark tasks")
    parser.add_argument(
        "-m",
        "--model",
        action="append",
        dest="models",
        help="Model to use for the benchmark (can be specified multiple times, or use ALL for all tested models)",
    )
    args = parser.parse_args()

    # Handle models argument
    if args.models is None:
        # Default to gemini/gemini-2.0-flash if no models specified
        models = ["gemini/gemini-2.0-flash"]
    elif "ALL" in args.models:
        # Get all tested models
        models = get_all_tested_models()
        if not models:
            print("No previously tested models found in benchmark_logs directory.")
            return
        print(f"Found {len(models)} previously tested models: {', '.join(models)}")
    else:
        # Use explicitly specified models
        models = args.models

    print(f"Running benchmark for models: {', '.join(models)}\n")

    # Load the tasks from YAML using pathlib
    tasks_file = Path(__file__).parent / "benchmark_tasks/basic_tasks.yaml"

    # Use ruamel.yaml to preserve original formatting
    yaml_obj = YAML()
    yaml_obj.preserve_quotes = True
    data = yaml_obj.load(tasks_file.read_text(encoding="utf-8"))

    system_prompt = data["system_prompt"]
    tasks = data["tasks"]

    # Run benchmark for each model
    for model_name in models:
        print(f"\n{'='*60}")
        print(f"Running benchmark for model: {model_name}")
        print(f"{'='*60}")

        # Ensure model metadata file exists
        ensure_model_metadata_exists(model_name)

        # Read existing logs for this model variation
        existing_logs = get_existing_logs(model_name, system_prompt)
        completed_prompts = get_completed_tasks(existing_logs)

        print(f"Found {len(existing_logs)} existing log files for this model variation")
        print(f"Already completed {len(completed_prompts)} tasks\n")

        # Filter tasks to only run those not completed yet
        tasks_to_run = [
            task for task in tasks if task["prompt"] not in completed_prompts
        ]

        if not tasks_to_run:
            print("All tasks have already been completed for this model variation!")
            # Model metadata file has already been created earlier in the loop
            continue

        print(f"Running {len(tasks_to_run)} new tasks...\n")

        total_tasks_run = len(tasks_to_run)
        correct = 0
        new_results = []

        # Check if model is available before processing tasks
        try:
            model = llm.get_model(model_name)
        except Exception as e:
            print(f"Error: Model '{model_name}' not found or not available: {e}")
            print(f"Skipping model '{model_name}' and continuing with next model...")
            continue

        for i, task in enumerate(tasks_to_run):
            prompt = task["prompt"]
            reference = task["reference"].strip().lower()

            full_prompt = system_prompt.format(prompt=prompt)

            # Time the task execution
            start_time = time.time()

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
            task_result = {
                "prompt": task["prompt"],
                "answer": response_text,
                "is_correct": is_correct,
                "duration_seconds": round(duration, 2),
            }
            new_results.append(task_result)

            # Save the task result immediately to the log file
            save_task_result(model_name, system_prompt, task_result)

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
        overall_score = (
            (overall_correct / total_completed) if total_completed > 0 else 0
        )
        print(
            f"Overall score: {overall_correct}/{total_completed} correct ({overall_score:.1f}%)"
        )

        # Note: Individual task results have already been saved during execution
        # This final save is kept for backward compatibility
        if new_results:
            append_to_today_log(model_name, system_prompt, tasks, new_results)


if __name__ == "__main__":
    main()
