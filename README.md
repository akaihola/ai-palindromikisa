# AI Palindromikisa

AI Palindrome Benchmark - evaluating LLM capability for creating palindromes.

## Installation

```bash
uv sync
```

## Usage

### Run Benchmark

Test specific models:
```bash
uv run ai-palindromikisa benchmark -m gemini/gemini-2.0-flash
```

Test all configured models:
```bash
uv run ai-palindromikisa benchmark -m ALL
```

### View Statistics

Extract and display statistics from benchmark logs:
```bash
uv run ai-palindromikisa stats
```

### Alternative Commands

Use the script entry points directly:
```bash
uv run benchmark -m gemini/gemini-2.0-flash
```

## Project Structure

- `models/` - Model configuration files
- `benchmark_logs/` - YAML benchmark results
- `src/ai_palindromikisa/` - Source code
- `tests/` - Test files

## Available Models

See `models/README.md` for configured models. Model names must match `uv run llm models` output.