# Models Directory

This directory contains model configuration files referenced by benchmark logs in the `benchmark_logs/` directory.

## File Structure

Model configuration files follow this naming convention:
- `<model-name>-<variation-index>.yaml`
- Model names use dashes instead of slashes (e.g., `gemini-gemini-2.0-flash` instead of `gemini/gemini-2.0-flash`)
- Variation index is a 1-based number for different parameter variations

## File Format

Each model configuration file contains:

```yaml
# Model metadata
name: "llm-model-name"  # Must match 'llm models' output exactly
provider: "provider-name"
model_id: "actual-model-id"

# Model parameters
parameters:
  temperature: 0.7
  max_tokens: 1000
  top_p: 0.9
  top_k: 40

# Additional metadata
metadata:
  description: "Model description"
  context_length: 1048576
  cost_per_input_token: 0.000075
  cost_per_output_token: 0.0003
  capabilities:
    - text_generation
    - multimodal
  release_date: "2025-05-01"
  version: "1"

# Benchmark-specific configuration
benchmark:
  variation_index: 1
  created_for: "ai-palindromikisa"
  task_type: "palindrome_generation"
```

## Current Models

The following model configuration files are currently available:

- `anthropic-claude-haiku-4-5-20251001-1.yaml` - Anthropic Claude Haiku 4.5 (`openrouter/anthropic/claude-haiku-4.5`)
- `anthropic-claude-sonnet-4-5-1.yaml` - Anthropic Claude Sonnet 4.5 (`openrouter/anthropic/claude-sonnet-4.5`)
- `gemini-2.0-flash-1.yaml` - Google Gemini 2.0 Flash (`openrouter/google/gemini-2.0-flash-001`)
- `gemini-gemini-2.0-flash-1.yaml` - Google Gemini Gemini 2.0 Flash (`openrouter/google/gemini-2.0-flash-001`)
- `gemini-gemini-2.5-flash-1.yaml` - Google Gemini Gemini 2.5 Flash (`openrouter/google/gemini-2.5-flash`)
- `gemini-gemini-2.5-pro-1.yaml` - Google Gemini Gemini 2.5 Pro (`openrouter/google/gemini-2.5-pro`)
- `openrouter-z-ai-glm-4.6-1.yaml` - OpenRouter Z AI GLM 4.6 (`openrouter/z-ai/glm-4.6`)

## Usage

These files are referenced by the `model` field in benchmark log files. The benchmark system uses these files to:

1. Track which specific model configuration was used for testing
2. Enable future parameter variation testing
3. Provide metadata for model comparison and analysis

## Adding New Models

When testing a new model, create a corresponding configuration file in this directory following the format above. The `name:` field must exactly match the model name shown in `uv run llm models` output. The benchmark system will automatically reference it when generating log files.