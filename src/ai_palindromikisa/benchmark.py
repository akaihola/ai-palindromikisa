#!/usr/bin/env python3

import re
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


def main():
    # Load the tasks from YAML using pathlib
    tasks_file = Path(__file__).parent / "tasks.yaml"

    with open(tasks_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    system_prompt = data["system_prompt"]
    tasks = data["tasks"]

    total_tasks = len(tasks)
    correct = 0

    print("Running palindrome benchmark tasks...\n")

    for task in tasks:
        prompt = task["prompt"]
        reference = task["reference"].strip().lower()
        task_id = task["id"]

        full_prompt = f"{system_prompt}\n\n{prompt}"

        model = llm.get_model()
        response = model.prompt(full_prompt)
        response_text = extract_palindrome(response.text()).strip().lower()

        is_correct = response_text == reference
        if is_correct:
            correct += 1

        print(f"Task: {task_id}")
        print(f"Prompt: {prompt}")
        print(f"Response: {response_text}")
        print(f"Reference: {reference}")
        print(f"Match: {'Yes' if is_correct else 'No'}\n")

    score = (correct / total_tasks) * 100 if total_tasks > 0 else 0
    print(f"Final score: {correct}/{total_tasks} correct ({score:.1f}%)")


if __name__ == "__main__":
    main()
