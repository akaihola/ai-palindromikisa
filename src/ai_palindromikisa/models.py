from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML

from ai_palindromikisa.option_suffix import generate_option_suffix
from ai_palindromikisa.paths import MODELS_DIR


@dataclass
class ModelConfig:
    """Configuration for a model including name and options."""

    name: str
    options: dict[str, str | float | int | bool] = field(default_factory=dict)

    def get_display_name(self) -> str:
        """Get the display name in llm library format with verbose options.

        Examples:
            ModelConfig("openrouter/x-ai/grok-4") -> "openrouter/x-ai/grok-4"
            ModelConfig("openrouter/x-ai/grok-4", {"temperature": 1.0})
                -> "openrouter/x-ai/grok-4: temperature 1.0"
            ModelConfig("gpt-4o-mini", {"temperature": 0.3, "top_p": 0.9})
                -> "gpt-4o-mini: temperature 0.3, top_p 0.9"
        """
        if not self.options:
            return self.name
        options_str = ", ".join(f"{k} {v}" for k, v in sorted(self.options.items()))
        return f"{self.name}: {options_str}"

    def get_base_filename(self) -> str:
        """Get the base filename (without extension) for this model config.

        Examples:
            ModelConfig("openrouter/x-ai/grok-4") -> "openrouter-x-ai-grok-4"
            ModelConfig("openrouter/x-ai/grok-4", {"temperature": 0.3})
                -> "openrouter-x-ai-grok-4-t03"
        """
        model_filename = self.name.replace("/", "-")
        suffix = generate_option_suffix(self.options)
        return f"{model_filename}{suffix}"

    def get_model_file_path(self) -> Path:
        """Get the path to the model metadata file."""
        return MODELS_DIR / f"{self.get_base_filename()}.yaml"


def get_all_model_configs() -> list[ModelConfig]:
    """Extract model configurations from model files in the models directory."""
    if not MODELS_DIR.exists():
        print(f"Warning: Models directory '{MODELS_DIR}' not found.")
        print("Please create the models directory and add model configuration files.")
        return []

    configs = []
    model_files_found = 0

    for model_file in sorted(MODELS_DIR.glob("*.yaml")):
        if model_file.name == "README.md":
            continue
        model_files_found += 1
        try:
            yaml_obj = YAML()
            model_data = yaml_obj.load(model_file.read_text(encoding="utf-8"))
            # Extract the model name from the name field
            model_name = model_data.get("name", "")
            if model_name:
                options = model_data.get("options", {}) or {}
                config = ModelConfig(
                    name=model_name,
                    options=options,
                )
                configs.append(config)
                options_str = f" (options: {options})" if options else ""
                print(
                    f"Found model: {model_name}{options_str} (from {model_file.name})"
                )
            else:
                print(f"Warning: No 'name' field found in {model_file.name}")
        except Exception as e:
            print(f"Warning: Could not read model file {model_file.name}: {e}")

    if model_files_found == 0:
        print("No model configuration files found in models directory.")
    elif len(configs) == 0:
        print(
            f"Found {model_files_found} model files but none had valid 'name' fields."
        )

    return configs


def find_or_create_model_config(
    model_name: str, options: dict[str, str | float | int | bool]
) -> ModelConfig:
    """Find an existing model config matching name and options, or create a new one.

    Args:
        model_name: The model name (e.g., "openrouter/x-ai/grok-4")
        options: Dictionary of options (e.g., {"temperature": 0.3})

    Returns:
        ModelConfig with the appropriate options

    Raises:
        ValueError: If a model file exists but has different options than expected
    """
    config = ModelConfig(name=model_name, options=options)
    model_file_path = config.get_model_file_path()

    if model_file_path.exists():
        # Validate that existing file has matching options
        yaml_obj = YAML()
        model_data = yaml_obj.load(model_file_path.read_text(encoding="utf-8"))
        file_options = model_data.get("options", {}) or {}

        if not _options_match(options, file_options):
            raise ValueError(
                f"Model file {model_file_path} exists but has different options. "
                f"Expected: {options}, Found: {file_options}"
            )

        return config

    # File doesn't exist, create it
    _create_model_file(config)
    return config


def _options_match(
    opts1: dict[str, str | float | int | bool],
    opts2: dict[str, str | float | int | bool],
) -> bool:
    """Check if two option dictionaries match."""
    # Normalize both to handle empty dict vs None and type differences
    opts1 = opts1 or {}
    opts2 = opts2 or {}

    if set(opts1.keys()) != set(opts2.keys()):
        return False

    for key in opts1:
        # Compare values, handling numeric type differences
        v1, v2 = opts1[key], opts2[key]
        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            if float(v1) != float(v2):
                return False
        elif v1 != v2:
            return False

    return True


def _create_model_file(config: ModelConfig) -> Path:
    """Create a model metadata file for the given configuration."""
    model_file_path = config.get_model_file_path()

    # Ensure models directory exists
    model_file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create the model metadata
    model_metadata: dict = {"name": config.name}
    if config.options:
        model_metadata["options"] = dict(config.options)

    # Write the metadata file
    yaml_obj = YAML()
    yaml_obj.preserve_quotes = True
    yaml_obj.default_flow_style = False
    yaml_obj.allow_unicode = True

    # Convert to string and write using Path
    string_stream = StringIO()
    yaml_obj.dump(model_metadata, string_stream)
    model_file_path.write_text(string_stream.getvalue(), encoding="utf-8")

    print(f"Created model metadata file: {model_file_path}")
    return model_file_path


def ensure_model_metadata_exists(config: ModelConfig) -> Path:
    """Ensure the model metadata file exists for the given configuration.

    Args:
        config: ModelConfig with name and options

    Returns:
        Path to the model metadata file
    """
    model_file_path = config.get_model_file_path()

    # If the file already exists, return its path
    if model_file_path.exists():
        return model_file_path

    # Create the model metadata file
    return _create_model_file(config)


def load_model_config_from_path(model_path: str) -> ModelConfig | None:
    """Load a ModelConfig from a model path reference in benchmark logs.

    Args:
        model_path: Path like "models/openrouter-x-ai-grok-4-t1.yaml"

    Returns:
        ModelConfig if the file exists and is valid, None otherwise
    """
    # Handle relative path from benchmark logs
    if model_path.startswith("models/"):
        model_file = MODELS_DIR / model_path[7:]  # Remove "models/" prefix
    else:
        model_file = Path(model_path)

    if not model_file.exists():
        return None

    try:
        yaml_obj = YAML()
        model_data = yaml_obj.load(model_file.read_text(encoding="utf-8"))
        model_name = model_data.get("name", "")
        if not model_name:
            return None
        options = model_data.get("options", {}) or {}
        return ModelConfig(name=model_name, options=options)
    except Exception:
        return None


def get_display_name_from_path(model_path: str) -> str:
    """Get a display name from a model path, loading config if available.

    Args:
        model_path: Path like "models/openrouter-x-ai-grok-4-t1.yaml"

    Returns:
        Display name like "openrouter/x-ai/grok-4: temperature 1.0"
        Falls back to cleaned filename if config can't be loaded
    """
    config = load_model_config_from_path(model_path)
    if config:
        return config.get_display_name()

    # Fallback: extract from filename
    if model_path.startswith("models/"):
        model_name = model_path[7:]
    else:
        model_name = model_path
    if model_name.endswith(".yaml"):
        model_name = model_name[:-5]
    return model_name
