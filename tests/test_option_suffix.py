"""Tests for option suffix generation."""

import pytest

from ai_palindromikisa.option_suffix import (
    _format_option_value,
    _generate_abbreviations,
    generate_option_suffix,
)


class TestFormatOptionValue:
    """Tests for _format_option_value function."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            # Floats - basic cases
            (0.3, "03"),
            (1.0, "1"),
            (0.75, "075"),
            (0.9, "09"),
            (0.5, "05"),
            # Floats - edge cases
            (0.001, "0001"),
            (0.0001, "00001"),
            (10.5, "105"),
            (100.0, "100"),
            # Negative floats
            (-0.5, "-05"),
            (-1.0, "-1"),
            (-0.3, "-03"),
            # Integers
            (100, "100"),
            (42, "42"),
            (0, "0"),
            (-5, "-5"),
            # Booleans
            (True, "true"),
            (False, "false"),
            # Strings
            ("json", "json"),
            ("text", "text"),
            ("", ""),
        ],
    )
    def test_format_option_value(self, value, expected):
        """Test formatting various option values."""
        assert _format_option_value(value) == expected


class TestGenerateAbbreviations:
    """Tests for _generate_abbreviations function."""

    def test_empty_list(self):
        """Test with empty list."""
        assert _generate_abbreviations([]) == {}

    def test_single_simple_option(self):
        """Test single option without separators."""
        assert _generate_abbreviations(["temperature"]) == {"temperature": "t"}

    def test_single_option_with_underscore(self):
        """Test single option with underscore."""
        assert _generate_abbreviations(["top_p"]) == {"top_p": "tp"}
        assert _generate_abbreviations(["top_k"]) == {"top_k": "tk"}
        assert _generate_abbreviations(["max_tokens"]) == {"max_tokens": "mt"}

    def test_multiple_non_conflicting(self):
        """Test multiple options that don't conflict."""
        result = _generate_abbreviations(["temperature", "top_p"])
        assert result == {"temperature": "t", "top_p": "tp"}

    def test_top_k_and_top_p(self):
        """Test top_k and top_p don't conflict."""
        result = _generate_abbreviations(["top_k", "top_p"])
        assert result == {"top_k": "tk", "top_p": "tp"}

    def test_three_top_options(self):
        """Test temperature, top_k, and top_p."""
        result = _generate_abbreviations(["temperature", "top_k", "top_p"])
        assert result == {"temperature": "t", "top_k": "tk", "top_p": "tp"}

    def test_collision_same_initial(self):
        """Test options that would have the same initial abbreviation."""
        # top_p and top_prob both start with 'tp'
        result = _generate_abbreviations(["top_p", "top_prob"])
        assert result["top_p"] == "tp"  # First alphabetically keeps it
        assert result["top_prob"] == "tpr"  # Second expands

    def test_collision_simple_names(self):
        """Test simple names that collide on first letter."""
        result = _generate_abbreviations(["temp", "test"])
        assert result["temp"] == "t"  # First alphabetically
        assert result["test"] == "te"  # Expanded

    def test_preserves_case(self):
        """Test that case is preserved in abbreviations."""
        result = _generate_abbreviations(["Temperature", "temperature"])
        # T and t are different, no collision
        assert result["Temperature"] == "T"
        assert result["temperature"] == "t"

    def test_multiple_underscores(self):
        """Test option with multiple underscores."""
        result = _generate_abbreviations(["max_new_tokens"])
        assert result == {"max_new_tokens": "mnt"}


class TestGenerateOptionSuffix:
    """Tests for generate_option_suffix function."""

    def test_empty_options(self):
        """Test with no options returns empty string."""
        assert generate_option_suffix({}) == ""

    def test_single_float_option(self):
        """Test single float option."""
        assert generate_option_suffix({"temperature": 0.3}) == "-t03"
        assert generate_option_suffix({"temperature": 1.0}) == "-t1"
        assert generate_option_suffix({"temperature": 0.75}) == "-t075"

    def test_single_int_option(self):
        """Test single integer option."""
        assert generate_option_suffix({"max_tokens": 100}) == "-mt100"
        assert generate_option_suffix({"seed": 42}) == "-s42"

    def test_single_bool_option(self):
        """Test single boolean option."""
        assert generate_option_suffix({"stream": True}) == "-strue"
        assert generate_option_suffix({"stream": False}) == "-sfalse"

    def test_single_string_option(self):
        """Test single string option."""
        assert generate_option_suffix({"format": "json"}) == "-fjson"

    def test_multiple_options_sorted(self):
        """Test multiple options are sorted alphabetically."""
        # temperature comes before top_p alphabetically
        result = generate_option_suffix({"temperature": 0.3, "top_p": 0.9})
        assert result == "-t03-tp09"

        # Order in dict shouldn't matter
        result = generate_option_suffix({"top_p": 0.9, "temperature": 0.3})
        assert result == "-t03-tp09"

    def test_three_top_options(self):
        """Test temperature, top_k, and top_p together."""
        result = generate_option_suffix(
            {
                "temperature": 0.3,
                "top_k": 50,
                "top_p": 0.9,
            }
        )
        assert result == "-t03-tk50-tp09"

    def test_negative_value(self):
        """Test negative option value."""
        assert generate_option_suffix({"temperature": -0.5}) == "-t-05"

    def test_empty_string_value(self):
        """Test empty string option value."""
        assert generate_option_suffix({"format": ""}) == "-f"

    def test_mixed_types(self):
        """Test mix of different value types."""
        result = generate_option_suffix(
            {
                "temperature": 0.7,
                "max_tokens": 100,
                "stream": True,
            }
        )
        # Sorted: max_tokens, stream, temperature
        assert result == "-mt100-strue-t07"
