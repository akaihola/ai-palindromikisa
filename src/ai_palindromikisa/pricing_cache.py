"""Pricing cache for LiteLLM pricing data from GitHub."""

import json
import time
from pathlib import Path

import requests

LITELLM_PRICING_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "model_prices_and_context_window.json"
)
CACHE_DIR = Path.home() / ".cache" / "ai-palindromikisa"
CACHE_FILE = CACHE_DIR / "pricing.json"
CACHE_METADATA_FILE = CACHE_DIR / "pricing_metadata.json"
DEFAULT_CACHE_EXPIRY_HOURS = 24


def get_cache_age_hours() -> float | None:
    """
    Get the age of the cached pricing data in hours.

    Returns:
        Age in hours, or None if cache doesn't exist or metadata is invalid.
    """
    if not CACHE_METADATA_FILE.exists():
        return None

    try:
        metadata = json.loads(CACHE_METADATA_FILE.read_text(encoding="utf-8"))
        fetch_time = metadata.get("fetch_timestamp")
        if fetch_time is None:
            return None
        age_seconds = time.time() - fetch_time
        return age_seconds / 3600
    except (json.JSONDecodeError, OSError):
        return None


def is_cache_fresh(max_age_hours: float = DEFAULT_CACHE_EXPIRY_HOURS) -> bool:
    """
    Check if the cached pricing data is fresh (less than max_age_hours old).

    Args:
        max_age_hours: Maximum age in hours before cache is considered stale.

    Returns:
        True if cache exists and is fresh, False otherwise.
    """
    age = get_cache_age_hours()
    if age is None:
        return False
    return age < max_age_hours


def fetch_pricing_from_github() -> dict | None:
    """
    Fetch pricing data from LiteLLM GitHub repository.

    Returns:
        Pricing dictionary, or None if fetch failed.
    """
    try:
        response = requests.get(LITELLM_PRICING_URL, timeout=30)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"Warning: Failed to fetch pricing from GitHub: {e}")
        return None


def save_pricing_to_cache(pricing_data: dict) -> bool:
    """
    Save pricing data to local cache.

    Args:
        pricing_data: The pricing dictionary to cache.

    Returns:
        True if save succeeded, False otherwise.
    """
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Save pricing data
        CACHE_FILE.write_text(json.dumps(pricing_data, indent=2), encoding="utf-8")

        # Save metadata with timestamp
        metadata = {
            "fetch_timestamp": time.time(),
            "source_url": LITELLM_PRICING_URL,
        }
        CACHE_METADATA_FILE.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        return True
    except OSError as e:
        print(f"Warning: Failed to save pricing cache: {e}")
        return False


def load_pricing_from_cache() -> dict | None:
    """
    Load pricing data from local cache.

    Returns:
        Pricing dictionary, or None if cache doesn't exist or is invalid.
    """
    if not CACHE_FILE.exists():
        return None

    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: Failed to load pricing cache: {e}")
        return None


def get_pricing_data(force_refresh: bool = False) -> dict:
    """
    Get pricing data with automatic caching.

    Priority:
    1. If force_refresh, fetch from GitHub
    2. Use local cache if fresh (< 24 hours old)
    3. If stale or missing, fetch from GitHub
    4. If GitHub fetch fails, use stale cache if available
    5. Return empty dict if no pricing available

    Args:
        force_refresh: If True, always fetch fresh data from GitHub.

    Returns:
        Pricing dictionary with model pricing information, or empty dict.
    """
    # Check if we should use cache
    if not force_refresh and is_cache_fresh():
        cached_data = load_pricing_from_cache()
        if cached_data is not None:
            return cached_data

    # Try to fetch from GitHub
    github_data = fetch_pricing_from_github()
    if github_data is not None:
        save_pricing_to_cache(github_data)
        return github_data

    # Try to load stale cache if GitHub failed
    cached_data = load_pricing_from_cache()
    if cached_data is not None:
        age = get_cache_age_hours()
        if age is not None:
            print(f"Warning: Using stale pricing cache ({age:.1f} hours old)")
        return cached_data

    # No pricing data available
    print("Warning: No pricing data available. Run 'ai-palindromikisa update-pricing'")
    return {}


def update_pricing_cache() -> bool:
    """
    Force update the pricing cache from GitHub.

    Returns:
        True if update succeeded, False otherwise.
    """
    github_data = fetch_pricing_from_github()
    if github_data is None:
        return False
    return save_pricing_to_cache(github_data)


def update_pricing_cli() -> None:
    """CLI entry point to update pricing cache from LiteLLM repository.

    Prints status and exits with code 1 on failure.
    """
    import sys

    if update_pricing_cache():
        print("Updated pricing data from LiteLLM repository")
    else:
        print("Failed to update pricing data from LiteLLM repository")
        sys.exit(1)
