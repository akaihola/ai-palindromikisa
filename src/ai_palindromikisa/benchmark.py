#!/usr/bin/env python3

import re
import time
from datetime import datetime, timezone

import llm

from ai_palindromikisa.cli import parse_cli_arguments
from ai_palindromikisa.formatting import format_price_for_console
from ai_palindromikisa.logs import (
    get_completed_tasks,
    get_existing_logs,
    save_task_result,
)
from ai_palindromikisa.models import (
    ModelConfig,
    ensure_model_metadata_exists,
    find_or_create_model_config,
)
from ai_palindromikisa.pricing import get_request_cost
from ai_palindromikisa.scores import show_scores
from ai_palindromikisa.tasks import load_tasks


def extract_palindrome(text):
    """Extract palindrome content from between <PALINDROMI> and </PALINDROMI> tags."""
    pattern = r"<PALINDROMI>(.*?)</PALINDROMI>"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


def truncate_long_response(response_text: str, reference: str) -> str:
    """Truncate response if longer than 1000 chars or 5x reference length.

    Args:
        response_text: The extracted palindrome response.
        reference: The correct reference answer.

    Returns:
        Original text if under threshold, otherwise truncated with indicator.
    """
    threshold = max(1000, 5 * len(reference))
    if len(response_text) <= threshold:
        return response_text

    # Keep 200 chars from start and end
    start_chars = 200
    end_chars = 200
    truncated_count = len(response_text) - start_chars - end_chars

    return (
        f"{response_text[:start_chars]}..."
        f"[{truncated_count} chars truncated]..."
        f"{response_text[-end_chars:]}"
    )


def normalize_text(text):
    """Normalize text by removing punctuation and converting to lowercase for comparison."""
    # Remove punctuation (commas, periods, exclamation marks, question marks, etc.)
    # and convert to lowercase for comparison
    import string

    # Remove punctuation
    text_no_punct = text.translate(str.maketrans("", "", string.punctuation))
    # Convert to lowercase and strip whitespace
    return text_no_punct.lower().strip()


def run_benchmark_for_config(
    config: ModelConfig, system_prompt: str, tasks: list
) -> None:
    """Run benchmark for a single model configuration."""
    separator = "=" * 60
    options_str = f" (options: {config.options})" if config.options else ""
    print(f"\n{separator}")
    print(f"Running benchmark for model: {config.name}{options_str}")
    print(f"Model file: {config.get_base_filename()}.yaml")
    print(separator)

    # Ensure model metadata file exists
    ensure_model_metadata_exists(config)

    # Read existing logs for this model configuration
    existing_logs = get_existing_logs(config, system_prompt)
    completed_prompts = get_completed_tasks(existing_logs)

    print(f"Found {len(existing_logs)} existing log files for this model configuration")
    print(f"Already completed {len(completed_prompts)} tasks\n")

    # Filter tasks to only run those not completed yet
    tasks_to_run = [task for task in tasks if task["prompt"] not in completed_prompts]

    if not tasks_to_run:
        print("All tasks have already been completed for this model configuration!")
        return

    print(f"Running {len(tasks_to_run)} new tasks...\n")

    total_tasks_run = len(tasks_to_run)
    correct = 0

    # Check if model is available before processing tasks
    try:
        model = llm.get_model(config.name)
    except Exception as e:
        print(f"Skipping missing '{config.name}'. Continuing with next model: {e}")
        return

    for task in tasks_to_run:
        reference = task["reference"].strip().lower()
        full_prompt = system_prompt.format(prompt=task["prompt"])

        # Time the task execution
        start_time = time.time()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        print(f"Prompt: {task['prompt']}")
        print(f"Reference: {reference}")

        # Pass options to model.prompt() if any are configured
        if config.options:
            response = model.prompt(full_prompt, **config.options)
        else:
            response = model.prompt(full_prompt)

        response_text = extract_palindrome(response.text()).strip().lower()
        response_text = truncate_long_response(response_text, reference)
        # Note: response_json is only populated after .text() consumes the stream
        response_json = response.response_json or {}

        end_time = time.time()
        duration = end_time - start_time

        # Get token counts from the response object (llm library stores them here)
        input_tokens = response.input_tokens or 0
        output_tokens = response.output_tokens or 0
        cost, cost_source = get_request_cost(
            config.name, input_tokens, output_tokens, response_json
        )

        # Build metadata with only the needed fields
        metadata = {}
        if input_tokens:
            metadata["input_tokens"] = input_tokens
        if output_tokens:
            metadata["output_tokens"] = output_tokens
        if cost is not None:
            metadata["cost_usd"] = cost
            metadata["cost_source"] = cost_source

        # Compare normalized text (ignoring punctuation)
        normalized_response = normalize_text(response_text)
        normalized_reference = normalize_text(reference)
        is_correct = normalized_response == normalized_reference
        if is_correct:
            correct += 1

        # Store result for logging - preserve original prompt formatting
        # Save the task result immediately to the log file
        save_task_result(
            config,
            system_prompt,
            task["prompt"],
            response_text,
            is_correct,
            duration,
            timestamp,
            metadata,
        )

        print(f"Response: {response_text}")
        print(f"Match: {'Yes' if is_correct else 'No'}")
        print(f"Duration: {duration:.2f}s")
        print(f"Cost: {format_price_for_console(cost, cost_source)}")
        print()

    show_scores(correct, total_tasks_run, completed_prompts, existing_logs)


def main() -> None:
    model_configs, limit = parse_cli_arguments()

    # For configs from CLI (not ALL), find or create matching model files
    resolved_configs = []
    for config in model_configs:
        resolved_config = find_or_create_model_config(config.name, config.options)
        resolved_configs.append(resolved_config)

    config_names = [
        c.name + (f" {c.options}" if c.options else "") for c in resolved_configs
    ]
    print(f"Running benchmark for models: {', '.join(config_names)}\n")

    system_prompt, tasks = load_tasks()

    # Apply limit if specified
    if limit is not None:
        tasks = tasks[:limit]

    # Run benchmark for each model configuration
    for config in resolved_configs:
        run_benchmark_for_config(config, system_prompt, tasks)


if __name__ == "__main__":
    main()
