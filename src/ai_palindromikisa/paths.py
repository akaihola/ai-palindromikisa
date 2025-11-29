"""Centralized path utilities for the project."""

from pathlib import Path

# Package directory (src/ai_palindromikisa/)
PACKAGE_DIR = Path(__file__).parent

# Project root directory (contains src/, models/, benchmark_logs/, etc.)
PROJECT_ROOT = PACKAGE_DIR.parent.parent

# Key directories
MODELS_DIR = PROJECT_ROOT / "models"
BENCHMARK_LOGS_DIR = PROJECT_ROOT / "benchmark_logs"
WEB_DIR = PACKAGE_DIR / "web"
BENCHMARK_TASKS_DIR = PACKAGE_DIR / "benchmark_tasks"

# Key files
BASIC_TASKS_FILE = BENCHMARK_TASKS_DIR / "basic_tasks.yaml"
