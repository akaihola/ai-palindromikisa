def show_scores(correct, total_tasks_run, completed_prompts, existing_logs):
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
