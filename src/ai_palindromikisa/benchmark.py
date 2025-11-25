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
from ai_palindromikisa.models import ensure_model_metadata_exists
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


def normalize_text(text):
    """Normalize text by removing punctuation and converting to lowercase for comparison."""
    # Remove punctuation (commas, periods, exclamation marks, question marks, etc.)
    # and convert to lowercase for comparison
    import string

    # Remove punctuation
    text_no_punct = text.translate(str.maketrans("", "", string.punctuation))
    # Convert to lowercase and strip whitespace
    return text_no_punct.lower().strip()


def main() -> None:
    models, limit = parse_cli_arguments()
    print(f"Running benchmark for models: {', '.join(models)}\n")

    system_prompt, tasks = load_tasks()

    # Run benchmark for each model
    separator = "=" * 60
    for model_name in models:
        print(f"\n{separator}")
        print(f"Running benchmark for model: {model_name}")
        print(separator)

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

        # Apply limit if specified
        if limit is not None:
            tasks_to_run = tasks_to_run[:limit]

        print(f"Running {len(tasks_to_run)} new tasks...\n")

        total_tasks_run = len(tasks_to_run)
        correct = 0

        # Check if model is available before processing tasks
        try:
            model = llm.get_model(model_name)
        except Exception as e:
            print(f"Skipping missing '{model_name}'. Continuing with next model: {e}")
            continue

        for task in tasks_to_run:
            reference = task["reference"].strip().lower()
            full_prompt = system_prompt.format(prompt=task["prompt"])

            # Time the task execution
            start_time = time.time()
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            print(f"Prompt: {task['prompt']}")
            print(f"Reference: {reference}")

            response = model.prompt(full_prompt)
            response_text = extract_palindrome(response.text()).strip().lower()
            # Note: response_json is only populated after .text() consumes the stream
            response_json = response.response_json or {}

            end_time = time.time()
            duration = end_time - start_time

            # Get token counts from the response object (llm library stores them here)
            input_tokens = response.input_tokens or 0
            output_tokens = response.output_tokens or 0
            cost, cost_source = get_request_cost(
                model_name, input_tokens, output_tokens, response_json
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
                model_name,
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

if __name__ == "__main__":
    main()
