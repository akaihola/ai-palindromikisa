"""Tests for benchmark logging functionality."""

import tempfile
from pathlib import Path
from typing import cast

import pytest
import yaml

from ai_palindromikisa.logs import save_task_result


class TestCreateLogFileIntegration:
    """Integration tests for save_task_result function."""

    @pytest.fixture
    def mock_system_prompt(self):
        """Mock system prompt for testing."""
        return """Olet erinomainen palindromien kirjoittaja.
Luo tai täydennä pyydetynlainen palindromi.
Sisällytä vastaukseen aina koko palindromi, myös täydentämistehtävissä.
Ympäröi luomasi palindromi XML-tageilla <PALINDROMI> ja </PALINDROMI>."""

    @pytest.fixture
    def mock_tasks(self):
        """Mock tasks for testing."""
        return [
            {
                "id": "test_1",
                "prompt": "Test prompt 1",
                "type": "generate",
                "reference": "test1",
            },
            {
                "id": "test_2",
                "prompt": "Test prompt 2",
                "type": "complete",
                "reference": "test2",
            },
        ]

    @pytest.fixture
    def mock_results(self):
        """Mock results for testing."""
        return [
            {
                "prompt": "Test prompt 1",
                "answer": "test1",
                "is_correct": True,
                "duration_seconds": 1.23,
            },
            {
                "prompt": "Test prompt 2",
                "answer": "wrong",
                "is_correct": False,
                "duration_seconds": 2.45,
            },
        ]

    def test_create_log_file_integration(
        self, mock_system_prompt, mock_tasks, mock_results
    ):
        """Test log file creation with real file system operations."""
        model_name = "test/test-model"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a temporary benchmark.py file in the expected location
            src_dir = temp_path / "src" / "ai_palindromikisa"
            src_dir.mkdir(parents=True, exist_ok=True)
            benchmark_file = src_dir / "benchmark.py"
            benchmark_file.write_text("# dummy file")

            # Patch the __file__ path to use our temp directory
            import ai_palindromikisa.benchmark

            original_file = ai_palindromikisa.benchmark.__file__
            ai_palindromikisa.benchmark.__file__ = str(benchmark_file)

            try:
                # Create the log file
                log_path = save_task_result(
                    model_name,
                    mock_system_prompt,
                    mock_results[0]["prompt"],
                    mock_results[0]["answer"],
                    mock_results[0]["is_correct"],
                    mock_results[0]["duration_seconds"],
                )
                assert (
                    save_task_result(
                        model_name,
                        mock_system_prompt,
                        mock_results[1]["prompt"],
                        mock_results[1]["answer"],
                        mock_results[1]["is_correct"],
                        mock_results[1]["duration_seconds"],
                    )
                    == log_path
                )

                # Verify file was created
                assert log_path.exists()

                # Load and verify the YAML content
                data = cast(
                    "dict", yaml.safe_load(log_path.read_text(encoding="utf-8"))
                )

                # Verify required top-level fields
                assert "date" in data
                assert "model" in data
                assert "prompt_template" in data
                assert "tasks" in data

                # Verify date format (YYYY-MM-DD)
                date_str = data["date"]
                assert len(date_str) == 10
                assert date_str[4] == "-" and date_str[7] == "-"

                # Verify model path format
                assert data["model"] == "models/test-test-model-1.yaml"

                # Verify prompt template contains system prompt and placeholder
                assert mock_system_prompt in data["prompt_template"]
                assert "{prompt}" in data["prompt_template"]

                # Verify tasks structure
                tasks = data["tasks"]
                assert len(tasks) == 2

                for i, task in enumerate(tasks):
                    assert "prompt" in task
                    assert "answer" in task
                    assert "is_correct" in task
                    assert "duration_seconds" in task

                    # Verify specific task data
                    assert task["prompt"] == mock_results[i]["prompt"]
                    assert task["answer"] == mock_results[i]["answer"]
                    assert task["is_correct"] == mock_results[i]["is_correct"]
                    assert (
                        task["duration_seconds"] == mock_results[i]["duration_seconds"]
                    )

                    # Verify data types
                    assert isinstance(task["prompt"], str)
                    assert isinstance(task["answer"], str)
                    assert isinstance(task["is_correct"], bool)
                    assert isinstance(task["duration_seconds"], (int, float))

                # Verify directory structure
                assert log_path.parent.name == "benchmark_logs"
                assert log_path.parent.parent == temp_path

            finally:
                # Restore original __file__
                ai_palindromikisa.benchmark.__file__ = original_file

    def test_model_name_conversion(self, mock_system_prompt, mock_tasks, mock_results):
        """Test that model names with slashes are properly converted to dashes."""
        model_name = "gemini/gemini-2.0-flash"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create temporary benchmark.py
            src_dir = temp_path / "src" / "ai_palindromikisa"
            src_dir.mkdir(parents=True, exist_ok=True)
            benchmark_file = src_dir / "benchmark.py"
            benchmark_file.write_text("# dummy file")

            import ai_palindromikisa.benchmark

            original_file = ai_palindromikisa.benchmark.__file__
            ai_palindromikisa.benchmark.__file__ = str(benchmark_file)

            try:
                # Create the log file
                log_path = save_task_result(
                    model_name,
                    mock_system_prompt,
                    mock_results[0]["prompt"],
                    mock_results[0]["answer"],
                    mock_results[0]["is_correct"],
                    mock_results[0]["duration_seconds"],
                )
                assert (
                    save_task_result(
                        model_name,
                        mock_system_prompt,
                        mock_results[1]["prompt"],
                        mock_results[1]["answer"],
                        mock_results[1]["is_correct"],
                        mock_results[1]["duration_seconds"],
                    )
                    == log_path
                )

                data = cast(
                    "dict", yaml.safe_load(log_path.read_text(encoding="utf-8"))
                )

                # Verify model path conversion
                assert data["model"] == "models/gemini-gemini-2.0-flash-1.yaml"

                # Verify filename conversion
                assert "gemini-gemini-2.0-flash" in log_path.name

            finally:
                ai_palindromikisa.benchmark.__file__ = original_file

    def test_directory_creation(self, mock_system_prompt, mock_tasks, mock_results):
        """Test that the benchmark_logs directory is created if it doesn't exist."""
        model_name = "test/model"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create temporary benchmark.py
            src_dir = temp_path / "src" / "ai_palindromikisa"
            src_dir.mkdir(parents=True, exist_ok=True)
            benchmark_file = src_dir / "benchmark.py"
            benchmark_file.write_text("# dummy file")

            import ai_palindromikisa.benchmark

            original_file = ai_palindromikisa.benchmark.__file__
            ai_palindromikisa.benchmark.__file__ = str(benchmark_file)

            try:
                # Don't create benchmark_logs directory beforehand
                benchmark_logs_dir = temp_path / "benchmark_logs"
                assert not benchmark_logs_dir.exists()

                # Create the log file
                log_path = save_task_result(
                    model_name,
                    mock_system_prompt,
                    mock_results[0]["prompt"],
                    mock_results[0]["answer"],
                    mock_results[0]["is_correct"],
                    mock_results[0]["duration_seconds"],
                )
                assert (
                    save_task_result(
                        model_name,
                        mock_system_prompt,
                        mock_results[1]["prompt"],
                        mock_results[1]["answer"],
                        mock_results[1]["is_correct"],
                        mock_results[1]["duration_seconds"],
                    )
                    == log_path
                )

                # Verify directory was created
                assert benchmark_logs_dir.exists()
                assert benchmark_logs_dir.is_dir()

                # Verify file was created in the directory
                assert log_path.parent == benchmark_logs_dir
                assert log_path.exists()

            finally:
                ai_palindromikisa.benchmark.__file__ = original_file

    def test_filename_format(self, mock_system_prompt, mock_tasks, mock_results):
        """Test that log filename follows the expected format."""
        model_name = "test/test-model"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create temporary benchmark.py
            src_dir = temp_path / "src" / "ai_palindromikisa"
            src_dir.mkdir(parents=True, exist_ok=True)
            benchmark_file = src_dir / "benchmark.py"
            benchmark_file.write_text("# dummy file")

            import ai_palindromikisa.benchmark

            original_file = ai_palindromikisa.benchmark.__file__
            ai_palindromikisa.benchmark.__file__ = str(benchmark_file)

            try:
                # Create the log file
                log_path = save_task_result(
                    model_name,
                    mock_system_prompt,
                    mock_results[0]["prompt"],
                    mock_results[0]["answer"],
                    mock_results[0]["is_correct"],
                    mock_results[0]["duration_seconds"],
                )
                assert (
                    save_task_result(
                        model_name,
                        mock_system_prompt,
                        mock_results[1]["prompt"],
                        mock_results[1]["answer"],
                        mock_results[1]["is_correct"],
                        mock_results[1]["duration_seconds"],
                    )
                    == log_path
                )

                # Verify filename format: YYYY-MM-DD-model-name.yaml
                filename = log_path.name
                assert filename.endswith(".yaml")

                # Extract date part (first 10 characters should be YYYY-MM-DD)
                date_part = filename[:10]
                assert len(date_part) == 10
                assert date_part[4] == "-" and date_part[7] == "-"

                # Verify model name part (after date, before .yaml)
                model_part = filename[11:-5]  # Remove date and .yaml
                assert model_part == "test-test-model"

            finally:
                ai_palindromikisa.benchmark.__file__ = original_file
