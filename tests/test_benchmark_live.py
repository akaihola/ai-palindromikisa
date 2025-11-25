"""Live API tests for benchmark functionality.

These tests call real LLM APIs and are not run by default.
Run with: pytest -m live
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import cast
from unittest import mock

import llm
import pytest
import yaml

import ai_palindromikisa.logs
from ai_palindromikisa.benchmark import extract_palindrome
from ai_palindromikisa.logs import save_task_result


# Mark all tests in this module as live (requires real API calls)
pytestmark = pytest.mark.live


class TestBenchmarkLiveAPI:
    """Live API tests for benchmark with real model calls."""

    # Use one of the cheapest models available
    MODEL_NAME = "gemini/gemini-2.0-flash-lite"

    @pytest.fixture
    def system_prompt(self):
        """System prompt for testing."""
        return """Olet erinomainen palindromien kirjoittaja.
Luo tai täydennä pyydetynlainen palindromi.
Sisällytä vastaukseen aina koko palindromi, myös täydentämistehtävissä.
Ympäröi luomasi palindromi XML-tageilla <PALINDROMI> ja </PALINDROMI>.

Esimerkki:
TEHTÄVÄ:
Luo seuraavanlainen palindromi:
Antti saa Totilta toteamuksen, että otti naiset, leikkisästi Elli-nimiset sellaiset.
VASTAUS:
<PALINDROMI>"Ellit, naiset otit", Totti totesi Antille.</PALINDROMI>

TEHTÄVÄ
Luo seuraavanlainen palindromi:
{prompt}
VASTAUS:"""

    @pytest.fixture
    def simple_task(self):
        """A simple task for testing."""
        return {
            "prompt": "Suomalainen kaksikirjaiminen paikannimi",
            "reference": "Ii",
        }

    @pytest.fixture
    def temp_project_structure(self, tmp_path: Path):
        """Create temporary project structure for logs."""
        src_dir = tmp_path / "src" / "ai_palindromikisa"
        src_dir.mkdir(parents=True, exist_ok=True)
        benchmark_file = src_dir / "benchmark.py"
        benchmark_file.write_text("# dummy file")

        # Create models directory
        models_dir = tmp_path / "models"
        models_dir.mkdir(parents=True, exist_ok=True)

        return tmp_path, benchmark_file

    def test_single_task_with_real_model(
        self,
        temp_project_structure: tuple[Path, Path],
        system_prompt: str,
        simple_task: dict,
    ):
        """Test running a single task with a real model and verify log format.

        This test verifies that the benchmark log contains:
        - All existing fields (prompt, answer, is_correct, duration_seconds)
        - New timestamp field (ISO-8601 UTC)
        - New metadata field (structured response data from llm)
        """
        tmp_path, benchmark_file = temp_project_structure
        prompt = simple_task["prompt"]
        reference = simple_task["reference"]

        # Get the model
        model = llm.get_model(self.MODEL_NAME)

        # Build full prompt
        full_prompt = system_prompt.format(prompt=prompt)

        # Record timestamp before request (for validation)
        timestamp_before = datetime.now(timezone.utc)

        # Make the actual API call
        response = model.prompt(full_prompt)
        response_text = extract_palindrome(response.text()).strip().lower()

        # Record timestamp after request
        timestamp_after = datetime.now(timezone.utc)

        # Determine correctness (simplified check)
        is_correct = response_text.lower() == reference.lower()

        # Duration (we don't have exact timing here, use a placeholder)
        duration = 1.0

        # Get response metadata from the llm response object
        # The response object has various attributes we can extract
        metadata = {}
        if hasattr(response, "response_json"):
            metadata = response.response_json or {}

        # Create timestamp in ISO-8601 UTC format
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Patch __file__ to use temp directory and save result
        with mock.patch.object(ai_palindromikisa.logs, "__file__", str(benchmark_file)):
            log_path = save_task_result(
                model_name=self.MODEL_NAME,
                system_prompt=system_prompt,
                prompt=prompt,
                response_text=response_text,
                is_correct=is_correct,
                duration=duration,
                timestamp=timestamp,
                metadata=metadata,
            )

            # Verify log file was created
            assert log_path.exists(), f"Log file was not created at {log_path}"

            # Load and verify log content
            log_data = cast(
                "dict", yaml.safe_load(log_path.read_text(encoding="utf-8"))
            )

            # Verify root-level fields
            assert "date" in log_data
            assert "model" in log_data
            assert "prompt_template" in log_data
            assert "tasks" in log_data

            # Verify tasks array has one task
            tasks = log_data["tasks"]
            assert len(tasks) == 1

            task = tasks[0]

            # Verify existing required fields
            assert "prompt" in task, "Task missing 'prompt' field"
            assert "answer" in task, "Task missing 'answer' field"
            assert "is_correct" in task, "Task missing 'is_correct' field"
            assert "duration_seconds" in task, "Task missing 'duration_seconds' field"

            # Verify NEW required fields
            assert "timestamp" in task, "Task missing 'timestamp' field"
            assert "metadata" in task, "Task missing 'metadata' field"

            # Verify timestamp format (ISO-8601 UTC)
            task_timestamp = task["timestamp"]
            assert isinstance(task_timestamp, str), "timestamp should be a string"
            # Parse timestamp to validate format
            parsed_ts = datetime.fromisoformat(task_timestamp.replace("Z", "+00:00"))
            # Compare at second precision since timestamp format truncates microseconds
            assert parsed_ts >= timestamp_before.replace(
                microsecond=0
            ), "timestamp should be after request start"
            assert parsed_ts <= timestamp_after.replace(microsecond=0) + __import__(
                "datetime"
            ).timedelta(seconds=10), "timestamp should be near request time"

            # Verify metadata is a dict/mapping
            task_metadata = task["metadata"]
            assert isinstance(
                task_metadata, dict
            ), f"metadata should be a dict, got {type(task_metadata)}"

            # Verify task content
            assert task["prompt"] == prompt
            assert isinstance(task["answer"], str)
            assert isinstance(task["is_correct"], bool)
            assert isinstance(task["duration_seconds"], (int, float))

            # Print results for debugging
            print(f"\nModel response: {response_text}")
            print(f"Is correct: {is_correct}")
            print(f"Timestamp: {task_timestamp}")
            print(f"Metadata keys: {list(task_metadata.keys())}")

    def test_metadata_contains_model_response_data(
        self,
        temp_project_structure: tuple[Path, Path],
        system_prompt: str,
        simple_task: dict,
    ):
        """Test that metadata contains structured data from the model response."""
        tmp_path, benchmark_file = temp_project_structure
        prompt = simple_task["prompt"]

        # Get the model
        model = llm.get_model(self.MODEL_NAME)

        # Build full prompt and make API call
        full_prompt = system_prompt.format(prompt=prompt)
        response = model.prompt(full_prompt)
        response_text = extract_palindrome(response.text()).strip().lower()

        # Extract metadata from llm response
        # Different models may have different response attributes
        metadata = {}

        # Try to get response_json which contains model-specific metadata
        if hasattr(response, "response_json") and response.response_json:
            metadata = response.response_json

        # Create timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        with mock.patch.object(ai_palindromikisa.logs, "__file__", str(benchmark_file)):
            log_path = save_task_result(
                model_name=self.MODEL_NAME,
                system_prompt=system_prompt,
                prompt=prompt,
                response_text=response_text,
                is_correct=True,  # Not important for this test
                duration=1.0,
                timestamp=timestamp,
                metadata=metadata,
            )

            log_data = cast(
                "dict", yaml.safe_load(log_path.read_text(encoding="utf-8"))
            )
            task = log_data["tasks"][0]

            # Metadata should be present even if empty
            assert "metadata" in task
            assert isinstance(task["metadata"], dict)

            # If we got metadata from the response, verify it was saved
            if metadata:
                assert task["metadata"] == metadata
                print(f"\nMetadata captured: {task['metadata']}")
            else:
                print("\nNo metadata available from model response (empty dict)")
