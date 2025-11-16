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


def create_log_file(model_name, system_prompt, tasks, results):
    """Create a benchmark log file according to the specification."""
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
    prompt_template = f"""{system_prompt}

{{prompt}}"""

    # Create log data structure
    log_data = {
        "date": date_str,
        "model": model_path,
        "prompt_template": prompt_template,
        "tasks": results,
    }

    # Write to file
    log_path.write_text(
        yaml.dump(log_data, default_flow_style=False, allow_unicode=True),
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

    data = yaml.safe_load(tasks_file.read_text(encoding="utf-8"))

    system_prompt = data["system_prompt"]
    tasks = data["tasks"]

    total_tasks = len(tasks)
    correct = 0
    results = []

    print("Running palindrome benchmark tasks...\n")

    for task in tasks:
        prompt = task["prompt"]
        reference = task["reference"].strip().lower()
        task_id = task["id"]

        full_prompt = f"{system_prompt}\n\n{prompt}"

        # Time the task execution
        start_time = time.time()

        model = llm.get_model(args.model)
        response = model.prompt(full_prompt)
        response_text = extract_palindrome(response.text()).strip().lower()

        end_time = time.time()
        duration = end_time - start_time

        is_correct = response_text == reference
        if is_correct:
            correct += 1

        # Store result for logging
        task_result = {
            "prompt": prompt,
            "answer": response_text,
            "is_correct": is_correct,
            "duration_seconds": round(duration, 2),
        }
        results.append(task_result)

        print(f"Task: {task_id}")
        print(f"Prompt: {prompt}")
        print(f"Response: {response_text}")
        print(f"Reference: {reference}")
        print(f"Match: {'Yes' if is_correct else 'No'}")
        print(f"Duration: {duration:.2f}s\n")

    score = (correct / total_tasks) * 100 if total_tasks > 0 else 0
    print(f"Final score: {correct}/{total_tasks} correct ({score:.1f}%)")

    # Create log file
    create_log_file(args.model, system_prompt, tasks, results)


if __name__ == "__main__":
    main()
