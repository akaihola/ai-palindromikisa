"""Tests for pricing calculation functionality."""

import pytest
from unittest import mock

from ai_palindromikisa import pricing


class TestExtractCostFromMetadata:
    """Tests for extract_cost_from_metadata function."""

    def test_openrouter_cost_in_usage(self):
        """Extracts cost from OpenRouter's usage.cost field."""
        metadata = {
            "id": "gen-xxx",
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "cost": 0.0001,
            },
        }
        assert pricing.extract_cost_from_metadata(metadata) == 0.0001

    def test_missing_usage_field(self):
        """Returns None when usage field is missing."""
        metadata = {"id": "gen-xxx"}
        assert pricing.extract_cost_from_metadata(metadata) is None

    def test_missing_cost_in_usage(self):
        """Returns None when cost field is missing from usage."""
        metadata = {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
            }
        }
        assert pricing.extract_cost_from_metadata(metadata) is None

    def test_empty_metadata(self):
        """Returns None for empty metadata."""
        assert pricing.extract_cost_from_metadata({}) is None

    def test_zero_cost(self):
        """Returns zero when cost is zero (free models)."""
        metadata = {"usage": {"cost": 0}}
        assert pricing.extract_cost_from_metadata(metadata) == 0


class TestGetRequestCost:
    """Tests for get_request_cost function."""

    def test_prefers_openrouter_cost(self):
        """Prefers OpenRouter actual cost over calculated cost."""
        metadata = {"usage": {"cost": 0.0001}}
        with mock.patch.object(
            pricing, "calculate_cost_from_tokens", return_value=0.0002
        ):
            cost, source = pricing.get_request_cost("model", 100, 50, metadata)
            assert cost == 0.0001
            assert source == "openrouter"

    def test_falls_back_to_litellm(self):
        """Falls back to LiteLLM calculation when OpenRouter cost not available."""
        metadata = {"usage": {"prompt_tokens": 100}}  # No cost field
        with mock.patch.object(
            pricing, "calculate_cost_from_tokens", return_value=0.0002
        ):
            cost, source = pricing.get_request_cost("model", 100, 50, metadata)
            assert cost == 0.0002
            assert source == "litellm"

    def test_returns_unknown_when_no_cost_available(self):
        """Returns unknown source when neither cost source is available."""
        metadata = {}
        with mock.patch.object(
            pricing, "calculate_cost_from_tokens", return_value=None
        ):
            cost, source = pricing.get_request_cost("model", 100, 50, metadata)
            assert cost is None
            assert source == "unknown"


class TestNormalizeModelNameForLitellm:
    """Tests for normalize_model_name_for_litellm function."""

    def test_simple_model_name(self):
        """Returns simple model name unchanged."""
        assert pricing.normalize_model_name_for_litellm("gpt-4o-mini") == "gpt-4o-mini"

    def test_removes_provider_prefix(self):
        """Removes provider prefix from model name."""
        assert (
            pricing.normalize_model_name_for_litellm(
                "anthropic/claude-3-haiku-20240307"
            )
            == "claude-3-haiku-20240307"
        )

    def test_gemini_flash_mapping(self):
        """Maps gemini-2.0-flash to experimental version."""
        assert (
            pricing.normalize_model_name_for_litellm("gemini/gemini-2.0-flash")
            == "gemini-2.0-flash-exp"
        )

    def test_other_gemini_models(self):
        """Other gemini models keep their name without provider prefix."""
        assert (
            pricing.normalize_model_name_for_litellm("gemini/gemini-1.5-pro")
            == "gemini-1.5-pro"
        )
