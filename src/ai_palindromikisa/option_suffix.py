"""Option suffix generation for model and log filenames."""

import re


def generate_option_suffix(options: dict[str, str | float | int | bool]) -> str:
    """Generate filename suffix from options dict.

    Returns empty string for no options, or '-abbrev1value1-abbrev2value2...'
    Options are sorted alphabetically.

    Examples:
        {} -> ""
        {"temperature": 0.3} -> "-t03"
        {"temperature": 1.0} -> "-t1"
        {"temperature": 0.3, "top_p": 0.9} -> "-t03-tp09"
    """
    if not options:
        return ""

    option_names = sorted(options.keys())
    abbreviations = _generate_abbreviations(option_names)

    parts = []
    for name in option_names:
        abbrev = abbreviations[name]
        value_str = _format_option_value(options[name])
        parts.append(f"{abbrev}{value_str}")

    return "-" + "-".join(parts)


def _generate_abbreviations(option_names: list[str]) -> dict[str, str]:
    """Generate unique abbreviations for option names.

    Algorithm:
    1. For each option name, create initial abbreviation by taking first char
       of each part when split at non-alpha chars (e.g., 'top_p' -> 'tp')
    2. Sort option names alphabetically
    3. Resolve collisions: for duplicates, alphabetically first keeps abbrev,
       later ones get more chars progressively

    Examples:
        ["temperature"] -> {"temperature": "t"}
        ["top_p"] -> {"top_p": "tp"}
        ["top_k", "top_p"] -> {"top_k": "tk", "top_p": "tp"}
        ["temperature", "top_p"] -> {"temperature": "t", "top_p": "tp"}
        ["top_p", "top_prob"] -> {"top_p": "tp", "top_prob": "tpr"}
    """
    if not option_names:
        return {}

    sorted_names = sorted(option_names)

    # Split each name into parts at non-alpha characters
    name_parts: dict[str, list[str]] = {}
    for name in sorted_names:
        parts = re.split(r"[^a-zA-Z]+", name)
        # Filter out empty strings
        name_parts[name] = [p for p in parts if p]

    # Generate initial abbreviations (first char of each part)
    abbreviations: dict[str, str] = {}
    for name in sorted_names:
        parts = name_parts[name]
        if parts:
            abbrev = "".join(p[0] for p in parts)
        else:
            # Fallback for names with no alpha chars (unlikely but handle it)
            abbrev = name[0] if name else ""
        abbreviations[name] = abbrev

    # Resolve collisions - alphabetically first keeps abbrev, later ones expand
    _resolve_collisions(sorted_names, abbreviations, name_parts)

    return abbreviations


def _resolve_collisions(
    sorted_names: list[str],
    abbreviations: dict[str, str],
    name_parts: dict[str, list[str]],
) -> None:
    """Resolve abbreviation collisions in place.

    For collisions, the alphabetically first name keeps the abbreviation,
    later names get progressively longer abbreviations.
    """
    # Group names by their current abbreviation
    abbrev_to_names: dict[str, list[str]] = {}
    for name in sorted_names:
        abbrev = abbreviations[name]
        if abbrev not in abbrev_to_names:
            abbrev_to_names[abbrev] = []
        abbrev_to_names[abbrev].append(name)

    # Process each group with collisions
    for abbrev, names in abbrev_to_names.items():
        if len(names) <= 1:
            continue

        # First name (alphabetically) keeps the abbreviation
        # Others need to be expanded
        for name in names[1:]:
            new_abbrev = _expand_abbreviation(
                name, name_parts[name], abbrev, set(abbreviations.values())
            )
            abbreviations[name] = new_abbrev


def _expand_abbreviation(
    name: str, parts: list[str], current_abbrev: str, used_abbrevs: set[str]
) -> str:
    """Expand an abbreviation to make it unique.

    Strategy: Add more characters from the last part first, then second-to-last, etc.
    This is because differentiation usually occurs in later parts
    (e.g., top_p vs top_prob differ in the last part).
    """
    if not parts:
        # Fallback for edge case
        counter = 1
        while f"{current_abbrev}{counter}" in used_abbrevs:
            counter += 1
        return f"{current_abbrev}{counter}"

    # Track how many chars we've used from each part
    # Start with 1 char from each part (which is current_abbrev)
    chars_per_part = [1] * len(parts)

    while True:
        # Try expanding from last part first, then second-to-last, etc.
        for part_idx in range(len(parts) - 1, -1, -1):
            part = parts[part_idx]
            if chars_per_part[part_idx] < len(part):
                chars_per_part[part_idx] += 1
                # Build new abbreviation
                new_abbrev = "".join(
                    parts[i][: chars_per_part[i]] for i in range(len(parts))
                )
                if new_abbrev not in used_abbrevs:
                    return new_abbrev

        # If all parts are exhausted, add a counter
        counter = 2
        while f"{current_abbrev}{counter}" in used_abbrevs:
            counter += 1
        return f"{current_abbrev}{counter}"


def _format_option_value(value: str | float | int | bool) -> str:
    """Format option value for filename.

    - Remove decimal points and trailing zeros for floats
    - Preserve negative signs
    - Boolean: 'true'/'false' as-is
    - String: as-is
    - Integer: as-is

    Examples:
        0.3 -> "03"
        1.0 -> "1"
        0.75 -> "075"
        -0.5 -> "-05"
        0.001 -> "0001"
        100 -> "100"
        True -> "true"
        "json" -> "json"
    """
    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, float):
        # Convert to string, remove decimal point and trailing zeros
        # But preserve leading zeros after removing decimal
        if value < 0:
            sign = "-"
            value = -value
        else:
            sign = ""

        # Format with enough precision to capture the value
        formatted = f"{value:.10f}".rstrip("0").rstrip(".")

        # Remove the decimal point
        if "." in formatted:
            int_part, dec_part = formatted.split(".")
            # If int part is 0, keep the leading zero
            if int_part == "0":
                result = "0" + dec_part
            else:
                result = int_part + dec_part
        else:
            result = formatted

        return sign + result

    if isinstance(value, int):
        return str(value)

    # String value
    return str(value)
