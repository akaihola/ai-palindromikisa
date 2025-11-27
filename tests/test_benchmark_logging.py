"""Tests for benchmark logging functionality."""

from pathlib import Path
from typing import cast
from unittest import mock

import pytest
import yaml

import ai_palindromikisa.logs
from ai_palindromikisa.logs import get_existing_logs, get_log_path, save_task_result
from ai_palindromikisa.models import ModelConfig


class TestGetLogPath:
    """Tests for get_log_path function."""

    @pytest.mark.parametrize(
        "name,options,expected_suffix",
        [
            ("test/model", {}, "test-model.yaml"),
            ("test/model", {"temperature": 0.3}, "test-model-t03.yaml"),
            ("openrouter/x-ai/grok-4", {}, "openrouter-x-ai-grok-4.yaml"),
            (
                "openrouter/x-ai/grok-4",
                {"temperature": 0.3},
                "openrouter-x-ai-grok-4-t03.yaml",
            ),
        ],
    )
    def test_log_path_includes_option_suffix(
        self, tmp_path: Path, name, options, expected_suffix
    ):
        """Test that log path includes option-based suffix."""
        config = ModelConfig(name=name, options=options)

        src_dir = tmp_path / "src" / "ai_palindromikisa"
        src_dir.mkdir(parents=True, exist_ok=True)
        logs_file = src_dir / "logs.py"
        logs_file.write_text("# dummy file")

        with mock.patch.object(ai_palindromikisa.logs, "__file__", str(logs_file)):
            log_path = get_log_path(config)

        assert log_path.name.endswith(expected_suffix)


class TestCreateLogFileIntegration:
    """Integration tests for save_task_result function."""

    @pytest.fixture
    def mock_system_prompt(self):
        """Mock system prompt for testing."""
        return """Olet erinomainen palindromien kirjoittaja.
Luo tai täydennä pyydetynlainen palindromi.
Sisällytä vastaukseen aina koko palindromi, myös täydentämistehtävissä.
Ympäröi luomasi palindromi XML-tageilla <PALINDROMI> ja </PALINDROMI>.
{prompt}"""

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
        self, tmp_path: Path, mock_system_prompt, mock_results
    ):
        """Test log file creation with real file system operations."""
        config = ModelConfig(name="test/test-model")

        # Create a temporary logs.py file in the expected location
        src_dir = tmp_path / "src" / "ai_palindromikisa"
        src_dir.mkdir(parents=True, exist_ok=True)
        logs_file = src_dir / "logs.py"
        logs_file.write_text("# dummy file")

        # Patch the __file__ path to use our temp directory
        with mock.patch.object(ai_palindromikisa.logs, "__file__", str(logs_file)):
            # Create the log file
            log_path = save_task_result(
                config,
                mock_system_prompt,
                mock_results[0]["prompt"],
                mock_results[0]["answer"],
                mock_results[0]["is_correct"],
                mock_results[0]["duration_seconds"],
                timestamp="2025-01-01T12:00:00Z",
                metadata={},
            )
            assert (
                save_task_result(
                    config,
                    mock_system_prompt,
                    mock_results[1]["prompt"],
                    mock_results[1]["answer"],
                    mock_results[1]["is_correct"],
                    mock_results[1]["duration_seconds"],
                    timestamp="2025-01-01T12:00:01Z",
                    metadata={"test_key": "test_value"},
                )
                == log_path
            )

            # Verify file was created
            assert log_path.exists()

            # Load and verify the YAML content
            data = cast("dict", yaml.safe_load(log_path.read_text(encoding="utf-8")))

            # Verify required top-level fields
            assert "date" in data
            assert "model" in data
            assert "prompt_template" in data
            assert "tasks" in data

            # Verify date format (YYYY-MM-DD)
            date_str = data["date"]
            assert len(date_str) == 10
            assert date_str[4] == "-" and date_str[7] == "-"

            # Verify model path format (no suffix for no options)
            assert data["model"] == "models/test-test-model.yaml"

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
                assert task["duration_seconds"] == mock_results[i]["duration_seconds"]

            # Verify directory structure
            assert log_path.parent.name == "benchmark_logs"
            assert log_path.parent.parent == tmp_path

    def test_model_name_conversion_with_options(
        self, tmp_path: Path, mock_system_prompt, mock_results
    ):
        """Test that model names and options are properly converted to filename."""
        config = ModelConfig(
            name="gemini/gemini-2.0-flash",
            options={"temperature": 0.3},
        )

        # Create temporary logs.py
        src_dir = tmp_path / "src" / "ai_palindromikisa"
        src_dir.mkdir(parents=True, exist_ok=True)
        logs_file = src_dir / "logs.py"
        logs_file.write_text("# dummy file")

        with mock.patch.object(ai_palindromikisa.logs, "__file__", str(logs_file)):
            # Create the log file
            log_path = save_task_result(
                config,
                mock_system_prompt,
                mock_results[0]["prompt"],
                mock_results[0]["answer"],
                mock_results[0]["is_correct"],
                mock_results[0]["duration_seconds"],
                timestamp="2025-01-01T12:00:00Z",
                metadata={},
            )

            data = cast("dict", yaml.safe_load(log_path.read_text(encoding="utf-8")))

            # Verify model path includes option suffix
            assert data["model"] == "models/gemini-gemini-2.0-flash-t03.yaml"

            # Verify filename includes option suffix
            assert "gemini-gemini-2.0-flash-t03" in log_path.name

    def test_directory_creation(self, tmp_path: Path, mock_system_prompt, mock_results):
        """Test that the benchmark_logs directory is created if it doesn't exist."""
        config = ModelConfig(name="test/model")

        # Create temporary logs.py
        src_dir = tmp_path / "src" / "ai_palindromikisa"
        src_dir.mkdir(parents=True, exist_ok=True)
        logs_file = src_dir / "logs.py"
        logs_file.write_text("# dummy file")

        with mock.patch.object(ai_palindromikisa.logs, "__file__", str(logs_file)):
            # Don't create benchmark_logs directory beforehand
            benchmark_logs_dir = tmp_path / "benchmark_logs"
            assert not benchmark_logs_dir.exists()

            # Create the log file
            log_path = save_task_result(
                config,
                mock_system_prompt,
                mock_results[0]["prompt"],
                mock_results[0]["answer"],
                mock_results[0]["is_correct"],
                mock_results[0]["duration_seconds"],
                timestamp="2025-01-01T12:00:00Z",
                metadata={},
            )

            # Verify directory was created
            assert benchmark_logs_dir.exists()
            assert benchmark_logs_dir.is_dir()

            # Verify file was created in the directory
            assert log_path.parent == benchmark_logs_dir
            assert log_path.exists()

    @pytest.mark.parametrize(
        "options,expected_suffix",
        [
            ({}, ".yaml"),
            ({"temperature": 0.3}, "-t03.yaml"),
            ({"temperature": 1.0}, "-t1.yaml"),
            ({"temperature": 0.3, "top_p": 0.9}, "-t03-tp09.yaml"),
        ],
    )
    def test_filename_format_with_options(
        self,
        tmp_path: Path,
        mock_system_prompt,
        mock_results,
        options,
        expected_suffix,
    ):
        """Test that log filename includes option-based suffix."""
        config = ModelConfig(name="test/test-model", options=options)

        # Create temporary logs.py
        src_dir = tmp_path / "src" / "ai_palindromikisa"
        src_dir.mkdir(parents=True, exist_ok=True)
        logs_file = src_dir / "logs.py"
        logs_file.write_text("# dummy file")

        with mock.patch.object(ai_palindromikisa.logs, "__file__", str(logs_file)):
            log_path = save_task_result(
                config,
                mock_system_prompt,
                mock_results[0]["prompt"],
                mock_results[0]["answer"],
                mock_results[0]["is_correct"],
                mock_results[0]["duration_seconds"],
                timestamp="2025-01-01T12:00:00Z",
                metadata={},
            )

            # Verify filename ends with expected suffix
            assert log_path.name.endswith(expected_suffix)

            # Verify filename format: YYYY-MM-DD-model-name[-options].yaml
            filename = log_path.name
            date_part = filename[:10]
            assert len(date_part) == 10
            assert date_part[4] == "-" and date_part[7] == "-"


class TestGetExistingLogs:
    """Tests for get_existing_logs function."""

    @pytest.fixture
    def mock_system_prompt(self):
        """Mock system prompt for testing."""
        return "Test system prompt\n{prompt}"

    def test_matches_by_model_field(self, tmp_path: Path, mock_system_prompt):
        """Test matching logs by model field in YAML."""
        config = ModelConfig(name="test/model", options={"temperature": 0.3})

        src_dir = tmp_path / "src" / "ai_palindromikisa"
        src_dir.mkdir(parents=True, exist_ok=True)
        logs_file = src_dir / "logs.py"
        logs_file.write_text("# dummy file")

        logs_dir = tmp_path / "benchmark_logs"
        logs_dir.mkdir()

        # Create a log file with matching model field
        log_content = {
            "date": "2025-01-01",
            "model": "models/test-model-t03.yaml",
            "prompt_template": mock_system_prompt,
            "tasks": [{"prompt": "test", "answer": "test", "is_correct": True}],
        }
        (logs_dir / "2025-01-01-test-model-t03.yaml").write_text(yaml.dump(log_content))

        # Create a log file for different options (should not match)
        log_content_no_opts = {
            "date": "2025-01-01",
            "model": "models/test-model.yaml",
            "prompt_template": mock_system_prompt,
            "tasks": [{"prompt": "other", "answer": "other", "is_correct": False}],
        }
        (logs_dir / "2025-01-01-test-model.yaml").write_text(
            yaml.dump(log_content_no_opts)
        )

        with mock.patch.object(ai_palindromikisa.logs, "__file__", str(logs_file)):
            logs = get_existing_logs(config, mock_system_prompt)

        assert len(logs) == 1
        assert logs[0]["model"] == "models/test-model-t03.yaml"

    def test_matches_by_filename_pattern(self, tmp_path: Path, mock_system_prompt):
        """Test matching logs by filename pattern."""
        config = ModelConfig(name="test/model")

        src_dir = tmp_path / "src" / "ai_palindromikisa"
        src_dir.mkdir(parents=True, exist_ok=True)
        logs_file = src_dir / "logs.py"
        logs_file.write_text("# dummy file")

        logs_dir = tmp_path / "benchmark_logs"
        logs_dir.mkdir()

        # Create a log file with matching filename pattern
        log_content = {
            "date": "2025-01-01",
            "model": "models/test-model.yaml",
            "prompt_template": mock_system_prompt,
            "tasks": [],
        }
        (logs_dir / "2025-01-01-test-model.yaml").write_text(yaml.dump(log_content))

        with mock.patch.object(ai_palindromikisa.logs, "__file__", str(logs_file)):
            logs = get_existing_logs(config, mock_system_prompt)

        assert len(logs) == 1

    def test_filters_by_system_prompt(self, tmp_path: Path, mock_system_prompt):
        """Test that logs are filtered by system prompt."""
        config = ModelConfig(name="test/model")

        src_dir = tmp_path / "src" / "ai_palindromikisa"
        src_dir.mkdir(parents=True, exist_ok=True)
        logs_file = src_dir / "logs.py"
        logs_file.write_text("# dummy file")

        logs_dir = tmp_path / "benchmark_logs"
        logs_dir.mkdir()

        # Create a log file with matching system prompt
        log_matching = {
            "date": "2025-01-01",
            "model": "models/test-model.yaml",
            "prompt_template": mock_system_prompt,
            "tasks": [],
        }
        (logs_dir / "2025-01-01-test-model.yaml").write_text(yaml.dump(log_matching))

        # Create a log file with different system prompt
        log_different = {
            "date": "2025-01-02",
            "model": "models/test-model.yaml",
            "prompt_template": "Different prompt\n{prompt}",
            "tasks": [],
        }
        (logs_dir / "2025-01-02-test-model.yaml").write_text(yaml.dump(log_different))

        with mock.patch.object(ai_palindromikisa.logs, "__file__", str(logs_file)):
            logs = get_existing_logs(config, mock_system_prompt)

        assert len(logs) == 1
        assert logs[0]["date"] == "2025-01-01"
