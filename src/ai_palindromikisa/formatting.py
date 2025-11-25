"""Formatting utilities for prices and other display values."""


def format_price_for_log(price: float | None) -> str | None:
    """
    Format price as human-readable decimal string for YAML logs.

    Avoids scientific notation by using explicit decimal formatting.
    Shows up to 10 decimal places, stripping trailing zeros.

    Examples:
    - 0.0000396 -> "0.0000396"
    - 0.001234567 -> "0.0012345670" -> "0.00123457"
    - 1.234e-10 -> "0.0000000001234"
    - None -> None

    Args:
        price: The price in USD, or None

    Returns:
        Formatted price string, or None if price is None
    """
    if price is None:
        return None

    # Use format specification to avoid scientific notation
    # Show up to 10 decimal places, strip trailing zeros
    formatted = f"{price:.10f}".rstrip("0").rstrip(".")

    # Ensure we always have at least one decimal place for clarity
    if "." not in formatted:
        formatted += ".0"

    return formatted


def format_price_for_console(price: float | None, source: str) -> str:
    """
    Format price for console display with source indicator.

    Args:
        price: The price in USD, or None
        source: The price source ("openrouter", "litellm", or other)

    Returns:
        Formatted string like "$0.0000396 (litellm)" or "Unknown"
    """
    if price is None:
        return "Unknown"

    # Format with 7 decimal places for console (covers most micro-prices)
    price_str = f"${price:.7f}".rstrip("0").rstrip(".")

    # Ensure we have at least "$0.0" format
    if price_str == "$":
        price_str = "$0.0"
    elif "." not in price_str:
        price_str += ".0"

    if source == "openrouter":
        return f"{price_str} (openrouter - actual)"
    elif source == "litellm":
        return f"{price_str} (litellm)"
    else:
        return f"{price_str} (source: {source})"
