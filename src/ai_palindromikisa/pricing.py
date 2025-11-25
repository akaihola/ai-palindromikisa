"""Pricing calculation using LiteLLM database and OpenRouter cost data."""

from ai_palindromikisa.pricing_cache import get_pricing_data

# Module-level cache for pricing data within a session
_pricing_data: dict | None = None


def _get_pricing_data() -> dict:
    """Get pricing data, using module-level cache for efficiency."""
    global _pricing_data
    if _pricing_data is None:
        _pricing_data = get_pricing_data()
    return _pricing_data


def normalize_model_name_for_litellm(model_name: str) -> str | None:
    """
    Convert llm model names to LiteLLM model names.

    Examples:
    - gpt-4o-mini -> gpt-4o-mini
    - anthropic/claude-3-haiku-20240307 -> claude-3-haiku-20240307
    - gemini/gemini-2.0-flash -> gemini-2.0-flash-exp
    """
    # Remove provider prefix if present
    if "/" in model_name:
        provider, model = model_name.split("/", 1)
        # For gemini, we might need to map to experimental versions
        if provider == "gemini" and model == "gemini-2.0-flash":
            return "gemini-2.0-flash-exp"
        return model

    return model_name


def calculate_cost_from_tokens(
    model_name: str, input_tokens: int, output_tokens: int
) -> float | None:
    """
    Calculate cost using LiteLLM's pricing database.

    Uses cached pricing data from GitHub.

    Returns cost in USD, or None if model not found in database.
    """
    litellm_model = normalize_model_name_for_litellm(model_name)
    pricing_data = _get_pricing_data()

    if litellm_model not in pricing_data:
        return None

    pricing = pricing_data[litellm_model]

    input_cost = input_tokens * pricing.get("input_cost_per_token", 0)
    output_cost = output_tokens * pricing.get("output_cost_per_token", 0)

    return input_cost + output_cost


def extract_cost_from_metadata(metadata: dict) -> float | None:
    """
    Extract cost from OpenRouter metadata if available.

    OpenRouter includes 'cost' field inside the 'usage' object.
    For BYOK (Bring Your Own Key) models, 'cost' is 0 and the actual cost
    is in 'cost_details.upstream_inference_cost'.
    """
    usage = metadata.get("usage", {})
    cost = usage.get("cost")

    # For BYOK models, cost is 0 but upstream_inference_cost has the actual value
    if cost == 0:
        cost_details = usage.get("cost_details", {})
        upstream_cost = cost_details.get("upstream_inference_cost")
        if upstream_cost is not None:
            return upstream_cost

    return cost


def get_request_cost(
    model_name: str, input_tokens: int, output_tokens: int, metadata: dict
) -> tuple[float | None, str]:
    """
    Get the cost of a request, preferring OpenRouter actual cost over calculated cost.

    Returns:
        (cost, source) where source is either "openrouter" or "litellm" or "unknown"
    """
    # First try OpenRouter actual cost
    openrouter_cost = extract_cost_from_metadata(metadata)
    if openrouter_cost is not None:
        return openrouter_cost, "openrouter"

    # Fall back to LiteLLM calculation
    calculated_cost = calculate_cost_from_tokens(
        model_name, input_tokens, output_tokens
    )
    if calculated_cost is not None:
        return calculated_cost, "litellm"

    return None, "unknown"
