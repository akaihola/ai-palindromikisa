"""Tests for pricing cache functionality."""

import json
import time
from pathlib import Path
from unittest import mock

import pytest

from ai_palindromikisa import pricing_cache


class TestCacheAgeHours:
    """Tests for get_cache_age_hours function."""

    def test_no_metadata_file(self, tmp_path):
        """Returns None when metadata file doesn't exist."""
        with mock.patch.object(
            pricing_cache, "CACHE_METADATA_FILE", tmp_path / "nonexistent.json"
        ):
            assert pricing_cache.get_cache_age_hours() is None

    def test_valid_metadata(self, tmp_path):
        """Returns correct age when metadata is valid."""
        metadata_file = tmp_path / "metadata.json"
        # Set timestamp to 2 hours ago
        two_hours_ago = time.time() - (2 * 3600)
        metadata_file.write_text(json.dumps({"fetch_timestamp": two_hours_ago}))

        with mock.patch.object(pricing_cache, "CACHE_METADATA_FILE", metadata_file):
            age = pricing_cache.get_cache_age_hours()
            assert age is not None
            assert 1.9 < age < 2.1  # Allow for small timing variations

    def test_invalid_json(self, tmp_path):
        """Returns None when metadata file has invalid JSON."""
        metadata_file = tmp_path / "metadata.json"
        metadata_file.write_text("not valid json")

        with mock.patch.object(pricing_cache, "CACHE_METADATA_FILE", metadata_file):
            assert pricing_cache.get_cache_age_hours() is None

    def test_missing_timestamp(self, tmp_path):
        """Returns None when timestamp field is missing."""
        metadata_file = tmp_path / "metadata.json"
        metadata_file.write_text(json.dumps({"other_field": "value"}))

        with mock.patch.object(pricing_cache, "CACHE_METADATA_FILE", metadata_file):
            assert pricing_cache.get_cache_age_hours() is None


class TestIsCacheFresh:
    """Tests for is_cache_fresh function."""

    def test_fresh_cache(self, tmp_path):
        """Returns True when cache is fresh."""
        metadata_file = tmp_path / "metadata.json"
        # Set timestamp to 1 hour ago (fresh for 24 hour default)
        one_hour_ago = time.time() - 3600
        metadata_file.write_text(json.dumps({"fetch_timestamp": one_hour_ago}))

        with mock.patch.object(pricing_cache, "CACHE_METADATA_FILE", metadata_file):
            assert pricing_cache.is_cache_fresh() is True

    def test_stale_cache(self, tmp_path):
        """Returns False when cache is stale."""
        metadata_file = tmp_path / "metadata.json"
        # Set timestamp to 25 hours ago (stale for 24 hour default)
        old_timestamp = time.time() - (25 * 3600)
        metadata_file.write_text(json.dumps({"fetch_timestamp": old_timestamp}))

        with mock.patch.object(pricing_cache, "CACHE_METADATA_FILE", metadata_file):
            assert pricing_cache.is_cache_fresh() is False

    def test_custom_max_age(self, tmp_path):
        """Respects custom max_age_hours parameter."""
        metadata_file = tmp_path / "metadata.json"
        # Set timestamp to 2 hours ago
        two_hours_ago = time.time() - (2 * 3600)
        metadata_file.write_text(json.dumps({"fetch_timestamp": two_hours_ago}))

        with mock.patch.object(pricing_cache, "CACHE_METADATA_FILE", metadata_file):
            # Stale with 1 hour max age
            assert pricing_cache.is_cache_fresh(max_age_hours=1) is False
            # Fresh with 3 hour max age
            assert pricing_cache.is_cache_fresh(max_age_hours=3) is True


class TestSaveAndLoadCache:
    """Tests for save_pricing_to_cache and load_pricing_from_cache functions."""

    def test_save_and_load_round_trip(self, tmp_path):
        """Data saved can be loaded back correctly."""
        cache_file = tmp_path / "pricing.json"
        metadata_file = tmp_path / "metadata.json"
        cache_dir = tmp_path

        test_data = {
            "gpt-4": {"input_cost_per_token": 0.00001, "output_cost_per_token": 0.00002}
        }

        with (
            mock.patch.object(pricing_cache, "CACHE_FILE", cache_file),
            mock.patch.object(pricing_cache, "CACHE_METADATA_FILE", metadata_file),
            mock.patch.object(pricing_cache, "CACHE_DIR", cache_dir),
        ):
            # Save
            assert pricing_cache.save_pricing_to_cache(test_data) is True
            assert cache_file.exists()
            assert metadata_file.exists()

            # Load
            loaded_data = pricing_cache.load_pricing_from_cache()
            assert loaded_data == test_data

    def test_load_nonexistent_cache(self, tmp_path):
        """Returns None when cache file doesn't exist."""
        with mock.patch.object(
            pricing_cache, "CACHE_FILE", tmp_path / "nonexistent.json"
        ):
            assert pricing_cache.load_pricing_from_cache() is None

    def test_load_invalid_json(self, tmp_path):
        """Returns None when cache file has invalid JSON."""
        cache_file = tmp_path / "pricing.json"
        cache_file.write_text("not valid json")

        with mock.patch.object(pricing_cache, "CACHE_FILE", cache_file):
            assert pricing_cache.load_pricing_from_cache() is None


class TestFetchPricingFromGitHub:
    """Tests for fetch_pricing_from_github function."""

    def test_successful_fetch(self):
        """Returns pricing data on successful fetch."""
        mock_response = mock.Mock()
        mock_response.json.return_value = {"gpt-4": {"input_cost_per_token": 0.00001}}
        mock_response.raise_for_status = mock.Mock()

        with mock.patch("requests.get", return_value=mock_response):
            result = pricing_cache.fetch_pricing_from_github()
            assert result == {"gpt-4": {"input_cost_per_token": 0.00001}}

    def test_network_error(self):
        """Returns None on network error."""
        import requests

        with mock.patch(
            "requests.get", side_effect=requests.RequestException("Network error")
        ):
            result = pricing_cache.fetch_pricing_from_github()
            assert result is None

    def test_invalid_json_response(self):
        """Returns None when response is not valid JSON."""
        mock_response = mock.Mock()
        mock_response.json.side_effect = json.JSONDecodeError("msg", "doc", 0)
        mock_response.raise_for_status = mock.Mock()

        with mock.patch("requests.get", return_value=mock_response):
            result = pricing_cache.fetch_pricing_from_github()
            assert result is None


class TestGetPricingData:
    """Tests for get_pricing_data function."""

    def test_uses_fresh_cache(self, tmp_path):
        """Uses cached data when cache is fresh."""
        cache_file = tmp_path / "pricing.json"
        metadata_file = tmp_path / "metadata.json"

        cached_data = {"model": {"input_cost_per_token": 0.001}}
        cache_file.write_text(json.dumps(cached_data))
        metadata_file.write_text(json.dumps({"fetch_timestamp": time.time()}))

        with (
            mock.patch.object(pricing_cache, "CACHE_FILE", cache_file),
            mock.patch.object(pricing_cache, "CACHE_METADATA_FILE", metadata_file),
            mock.patch(
                "ai_palindromikisa.pricing_cache.fetch_pricing_from_github"
            ) as mock_fetch,
        ):
            result = pricing_cache.get_pricing_data()
            assert result == cached_data
            mock_fetch.assert_not_called()

    def test_fetches_when_cache_stale(self, tmp_path):
        """Fetches from GitHub when cache is stale."""
        cache_file = tmp_path / "pricing.json"
        metadata_file = tmp_path / "metadata.json"
        cache_dir = tmp_path

        # Old cache
        old_data = {"old": {"input_cost_per_token": 0.001}}
        cache_file.write_text(json.dumps(old_data))
        old_timestamp = time.time() - (25 * 3600)  # 25 hours ago
        metadata_file.write_text(json.dumps({"fetch_timestamp": old_timestamp}))

        new_data = {"new": {"input_cost_per_token": 0.002}}

        with (
            mock.patch.object(pricing_cache, "CACHE_FILE", cache_file),
            mock.patch.object(pricing_cache, "CACHE_METADATA_FILE", metadata_file),
            mock.patch.object(pricing_cache, "CACHE_DIR", cache_dir),
            mock.patch(
                "ai_palindromikisa.pricing_cache.fetch_pricing_from_github",
                return_value=new_data,
            ),
        ):
            result = pricing_cache.get_pricing_data()
            assert result == new_data

    def test_force_refresh(self, tmp_path):
        """Force refresh fetches from GitHub even with fresh cache."""
        cache_file = tmp_path / "pricing.json"
        metadata_file = tmp_path / "metadata.json"
        cache_dir = tmp_path

        cached_data = {"cached": {"input_cost_per_token": 0.001}}
        cache_file.write_text(json.dumps(cached_data))
        metadata_file.write_text(json.dumps({"fetch_timestamp": time.time()}))

        new_data = {"fresh": {"input_cost_per_token": 0.002}}

        with (
            mock.patch.object(pricing_cache, "CACHE_FILE", cache_file),
            mock.patch.object(pricing_cache, "CACHE_METADATA_FILE", metadata_file),
            mock.patch.object(pricing_cache, "CACHE_DIR", cache_dir),
            mock.patch(
                "ai_palindromikisa.pricing_cache.fetch_pricing_from_github",
                return_value=new_data,
            ),
        ):
            result = pricing_cache.get_pricing_data(force_refresh=True)
            assert result == new_data

    def test_falls_back_to_stale_cache_on_fetch_failure(self, tmp_path):
        """Uses stale cache when GitHub fetch fails."""
        cache_file = tmp_path / "pricing.json"
        metadata_file = tmp_path / "metadata.json"

        stale_data = {"stale": {"input_cost_per_token": 0.001}}
        cache_file.write_text(json.dumps(stale_data))
        old_timestamp = time.time() - (25 * 3600)
        metadata_file.write_text(json.dumps({"fetch_timestamp": old_timestamp}))

        with (
            mock.patch.object(pricing_cache, "CACHE_FILE", cache_file),
            mock.patch.object(pricing_cache, "CACHE_METADATA_FILE", metadata_file),
            mock.patch(
                "ai_palindromikisa.pricing_cache.fetch_pricing_from_github",
                return_value=None,
            ),
        ):
            result = pricing_cache.get_pricing_data()
            assert result == stale_data

    def test_returns_empty_dict_when_no_data_available(self, tmp_path):
        """Returns empty dict when no cache and GitHub fetch fails."""
        with (
            mock.patch.object(
                pricing_cache, "CACHE_FILE", tmp_path / "nonexistent.json"
            ),
            mock.patch.object(
                pricing_cache, "CACHE_METADATA_FILE", tmp_path / "nonexistent_meta.json"
            ),
            mock.patch(
                "ai_palindromikisa.pricing_cache.fetch_pricing_from_github",
                return_value=None,
            ),
        ):
            result = pricing_cache.get_pricing_data()
            assert result == {}
