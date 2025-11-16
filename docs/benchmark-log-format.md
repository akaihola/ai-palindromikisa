# Benchmark Log YAML Format Specification

## File Structure

Benchmark log files use the `.yaml` extension and follow this naming convention:
- `benchmark_logs/YYYY-MM-DD-<model>.yaml`
- The `<model>` component corresponds to the `--model` argument, with filesystem slashes mapped to allowed characters
- Slash mapping: `/` → `-` (e.g., `gemini/gemini-2.0-flash` → `gemini-gemini-2.0-flash`)
- Example: `benchmark_logs/2024-12-01-gemini-gemini-2.0-flash.yaml`

## Root-Level Fields

```yaml
# Required fields
date: string                       # Date in YYYY-MM-DD format
model: string                      # Relative path to model file
prompt_template: string             # Template containing {prompt} placeholder
tasks: array                       # Individual task results
```

## Model Field

```yaml
model: string                      # Relative path to model file
# Format: models/<model>-<variation-index>
# <model>: Model name with slashes mapped to dashes (e.g., gemini-gemini-2.0-flash)
# <variation-index>: 1-based running index for different parameter variations
# Examples:
#   models/gemini-gemini-2.0-flash-1.yaml
#   models/anthropic-claude-3-sonnet-1.yaml
#   models/openai-gpt-4-turbo-2.yaml
```

## Prompt Template Field

```yaml
prompt_template: string             # Template string containing {prompt} placeholder
# The {prompt} placeholder is replaced with the task definition from the tasks YAML file
# The template includes the full system prompt for palindrome generation
```

## Task Result Objects

Each task result in the `tasks` array contains:

```yaml
- prompt: string                   # Task definition from tasks YAML file (excludes system prompt)
  answer: string                   # Extracted palindrome content from model response
  is_correct: boolean              # Whether answer matches reference
  duration_seconds: number         # Time taken for this task
```

## Complete Example

```yaml
date: "2024-12-01"
model: "models/gemini-gemini-2.0-flash-1.yaml"
prompt_template: |
  Olet erinomainen palindromien kirjoittaja.
  Luo tai täydennä pyydetynlainen palindromi.
  Sisällytä vastaukseen aina koko palindromi, myös täydentämistehtävissä.
  Ympäröi luomasi palindromi XML-tageilla <PALINDROMI> ja </PALINDROMI>.

  Esimerkki:
  TEHTÄVÄ:
  Luo seuraavanlainen palindromi:
  Antti saa Totilta toteamuksen, että otti naiset, leikkisästi Elli-nimiset sellaiset.
  VASTAUS:
  <PALINDROMI>"Ellit, naiset otit", Totti tovesi Antille.</PALINDROMI>

  TEHTÄVÄ
  Luo seuraavanlainen palindromi:
  VASTAUS:

  {prompt}
tasks:
  - prompt: "Suomalainen kaksikirjaiminen paikannimi"
    answer: "Ii"
    is_correct: true
    duration_seconds: 4.1

  - prompt: "Täydennä puuttuva kirjain: Assi _okaa kodissa."
    answer: "Assi tokaa kodissa."
    is_correct: false
    duration_seconds: 3.2
```

## Validation Rules

### Required Fields
- `date`, `model`, `prompt_template`, `tasks` are mandatory
- Each task must have: `prompt`, `answer`, `is_correct`, `duration_seconds`

### Data Types
- Date must be in YYYY-MM-DD format
- Durations must be in seconds (float)
- Boolean values must be `true` or `false` (lowercase)
- Prompt template must contain `{prompt}` placeholder

### Model Path Requirements
- Model path must be relative to project root
- Must follow format: `models/<model>-<variation-index>.yaml`
- <model> component must have slashes replaced with dashes
- <variation-index> must be a positive integer (1-based)

## Task Definition Format

Task definitions referenced by logs use this format:

```yaml
tasks:
  - prompt: "Suomalainen kaksikirjaiminen paikannimi"
    reference: "Ii"
  - prompt: "Kolmekirjaiminen sana, käytä vain kirjaimia T ja U"
    reference: "utu"
```

## Model Configuration Files

The `model` field references separate YAML files in the `models/` directory that contain:
- Model name and provider information
- Parameter settings (temperature, max_tokens, etc.)
- Version information
- Other model-specific metadata