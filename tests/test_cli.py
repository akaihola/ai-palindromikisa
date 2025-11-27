"""Tests for CLI argument parsing."""

import sys
from unittest import mock

import pytest

from ai_palindromikisa.cli import _parse_option_value, parse_cli_arguments
from ai_palindromikisa.models import ModelConfig


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


class TestParseCliArguments:
    """Tests for parse_cli_arguments function."""

    def test_default_model(self):
        """Test default model when no arguments provided."""
        with mock.patch.object(sys, "argv", ["benchmark"]):
            configs, limit = parse_cli_arguments()
            assert len(configs) == 1
            assert configs[0].name == "gemini/gemini-2.0-flash"
            assert configs[0].options == {}
            assert limit is None

    def test_single_model(self):
        """Test single model argument."""
        with mock.patch.object(sys, "argv", ["benchmark", "-m", "test/model"]):
            configs, limit = parse_cli_arguments()
            assert len(configs) == 1
            assert configs[0].name == "test/model"
            assert configs[0].options == {}

    def test_multiple_models(self):
        """Test multiple model arguments."""
        with mock.patch.object(
            sys, "argv", ["benchmark", "-m", "model1", "-m", "model2"]
        ):
            configs, limit = parse_cli_arguments()
            assert len(configs) == 2
            assert configs[0].name == "model1"
            assert configs[1].name == "model2"

    def test_single_option(self):
        """Test single -o option."""
        with mock.patch.object(
            sys, "argv", ["benchmark", "-m", "test/model", "-o", "temperature", "0.3"]
        ):
            configs, limit = parse_cli_arguments()
            assert len(configs) == 1
            assert configs[0].options == {"temperature": 0.3}

    def test_multiple_options(self):
        """Test multiple -o options."""
        with mock.patch.object(
            sys,
            "argv",
            [
                "benchmark",
                "-m",
                "test/model",
                "-o",
                "temperature",
                "0.3",
                "-o",
                "max_tokens",
                "100",
            ],
        ):
            configs, limit = parse_cli_arguments()
            assert configs[0].options == {"temperature": 0.3, "max_tokens": 100}

    def test_limit_argument(self):
        """Test --limit argument."""
        with mock.patch.object(
            sys, "argv", ["benchmark", "-m", "test/model", "-l", "5"]
        ):
            configs, limit = parse_cli_arguments()
            assert limit == 5

    def test_options_applied_to_all_models(self):
        """Test that options are applied to all specified models."""
        with mock.patch.object(
            sys,
            "argv",
            [
                "benchmark",
                "-m",
                "model1",
                "-m",
                "model2",
                "-o",
                "temperature",
                "0.5",
            ],
        ):
            configs, limit = parse_cli_arguments()
            assert len(configs) == 2
            assert configs[0].options == {"temperature": 0.5}
            assert configs[1].options == {"temperature": 0.5}
