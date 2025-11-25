"""Tests for price formatting utilities."""

import pytest

from ai_palindromikisa.formatting import format_price_for_console, format_price_for_log


class TestFormatPriceForLog:
    """Tests for format_price_for_log function."""

    def test_none_returns_none(self):
        """None input should return None."""
        assert format_price_for_log(None) is None

    def test_small_price_no_scientific_notation(self):
        """Small prices should be formatted as decimals, not scientific notation."""
        result = format_price_for_log(3.96e-05)
        assert result == "0.0000396"
        assert "e" not in result.lower()

    def test_very_small_price(self):
        """Very small prices should still be formatted as decimals."""
        result = format_price_for_log(1.234e-10)
        assert "e" not in result.lower()
        assert result.startswith("0.")

    def test_larger_price(self):
        """Larger prices should be formatted normally."""
        result = format_price_for_log(0.0123456)
        assert result == "0.0123456"

    def test_whole_number_price(self):
        """Whole number prices should have at least one decimal place."""
        result = format_price_for_log(1.0)
        assert result == "1.0"

    def test_trailing_zeros_stripped(self):
        """Trailing zeros should be stripped."""
        result = format_price_for_log(0.00100000)
        assert result == "0.001"

    def test_zero_price(self):
        """Zero should be formatted as 0.0."""
        result = format_price_for_log(0.0)
        assert result == "0.0"


class TestFormatPriceForConsole:
    """Tests for format_price_for_console function."""

    def test_none_returns_unknown(self):
        """None price should return 'Unknown'."""
        assert format_price_for_console(None, "litellm") == "Unknown"

    def test_litellm_source(self):
        """LiteLLM source should be formatted correctly."""
        result = format_price_for_console(0.0000396, "litellm")
        assert result == "$0.0000396 (litellm)"

    def test_openrouter_source(self):
        """OpenRouter source should include 'actual' indicator."""
        result = format_price_for_console(0.0000834, "openrouter")
        assert result == "$0.0000834 (openrouter - actual)"

    def test_unknown_source(self):
        """Unknown source should be formatted with source indicator."""
        result = format_price_for_console(0.001, "custom")
        assert result == "$0.001 (source: custom)"

    def test_no_scientific_notation(self):
        """Console output should not use scientific notation."""
        result = format_price_for_console(3.96e-05, "litellm")
        # Check only the price part (before the parentheses) for scientific notation
        price_part = result.split(" ")[0]  # "$0.0000396"
        assert "e" not in price_part.lower()

    def test_dollar_sign_present(self):
        """Console output should include dollar sign."""
        result = format_price_for_console(0.01, "litellm")
        assert result.startswith("$")

    def test_zero_price(self):
        """Zero price should be formatted correctly."""
        result = format_price_for_console(0.0, "litellm")
        assert "$0.0" in result
