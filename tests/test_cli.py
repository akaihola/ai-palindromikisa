"""Tests for CLI argument parsing."""

import pytest
from click.testing import CliRunner

from ai_palindromikisa.cli import _parse_option_value, cli, option_callback


class TestParseOptionValue:
    """Tests for _parse_option_value function."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            # Floats
            ("0.3", 0.3),
            ("1.5", 1.5),
            ("0.0", 0.0),
            # Integers
            ("42", 42),
            ("0", 0),
            ("100", 100),
            # Booleans
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("on", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("off", False),
            ("no", False),
            # Strings
            ("hello", "hello"),
            ("some-value", "some-value"),
            ("not_a_bool", "not_a_bool"),
        ],
    )
    def test_parse_option_value(self, value: str, expected):
        """Test parsing different option value types."""
        result = _parse_option_value(value)
        assert result == expected
        assert type(result) == type(expected)


class TestOptionCallback:
    """Tests for option_callback function."""

    def test_empty_options(self):
        """Test callback with no options."""
        result = option_callback(None, None, ())
        assert result == {}

    def test_single_option(self):
        """Test callback with single option."""
        result = option_callback(None, None, (("temperature", "0.3"),))
        assert result == {"temperature": 0.3}

    def test_multiple_options(self):
        """Test callback with multiple options."""
        result = option_callback(
            None, None, (("temperature", "0.3"), ("max_tokens", "100"))
        )
        assert result == {"temperature": 0.3, "max_tokens": 100}


class TestCli:
    """Tests for CLI commands."""

    def test_help(self):
        """Test main help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "AI-Palindromikisa" in result.output
        assert "benchmark" in result.output
        assert "stats" in result.output
        assert "tasks" in result.output

    def test_version(self):
        """Test version output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0

    def test_benchmark_help(self):
        """Test benchmark command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["benchmark", "--help"])
        assert result.exit_code == 0
        assert "--model" in result.output
        assert "--option" in result.output
        assert "--limit" in result.output

    def test_stats_help(self):
        """Test stats command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["stats", "--help"])
        assert result.exit_code == 0
        assert "Extract and display statistics" in result.output

    def test_tasks_help(self):
        """Test tasks command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["tasks", "--help"])
        assert result.exit_code == 0
        assert "task-level statistics" in result.output

    def test_serve_help(self):
        """Test serve command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["serve", "--help"])
        assert result.exit_code == 0
        assert "--port" in result.output
        assert "--build-only" in result.output
        assert "--output" in result.output

    def test_migrate_help(self):
        """Test migrate command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["migrate", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.output

    def test_delete_task_help(self):
        """Test delete-task command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["delete-task", "--help"])
        assert result.exit_code == 0
        assert "--search" in result.output
        assert "--force" in result.output

    def test_delete_task_requires_search(self):
        """Test delete-task requires --search option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["delete-task"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()
