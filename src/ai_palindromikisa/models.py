from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML


@dataclass
class ModelConfig:
    """Configuration for a model including name and options."""

    name: str
    options: dict[str, str | float | int | bool] = field(default_factory=dict)
    variation_index: int = 1

    def get_base_filename(self) -> str:
        """Get the base filename (without extension) for this model config."""
        model_filename = self.name.replace("/", "-")
        return f"{model_filename}-{self.variation_index}"

    def get_model_file_path(self) -> Path:
        """Get the path to the model metadata file."""
        models_dir = Path(__file__).parent.parent.parent / "models"
        return models_dir / f"{self.get_base_filename()}.yaml"


def get_all_model_configs() -> list[ModelConfig]:
    """Extract model configurations from model files in the models directory."""
    models_dir = Path(__file__).parent.parent.parent / "models"

    if not models_dir.exists():
        print(f"Warning: Models directory '{models_dir}' not found.")
        print("Please create the models directory and add model configuration files.")
        return []

    configs = []
    model_files_found = 0

    for model_file in sorted(models_dir.glob("*.yaml")):
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
                # Extract variation index from filename
                variation_index = _extract_variation_index(model_file.stem)
                config = ModelConfig(
                    name=model_name,
                    options=options,
                    variation_index=variation_index,
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


def _extract_variation_index(filename_stem: str) -> int:
    """Extract the variation index from a model filename stem.

    Args:
        filename_stem: Filename without extension (e.g., "openrouter-x-ai-grok-4-2")

    Returns:
        The variation index (e.g., 2), or 1 if not found
    """
    parts = filename_stem.rsplit("-", 1)
    if len(parts) == 2:
        try:
            return int(parts[1])
        except ValueError:
            pass
    return 1


def find_or_create_model_config(
    model_name: str, options: dict[str, str | float | int | bool]
) -> ModelConfig:
    """Find an existing model config matching name and options, or create a new one.

    Args:
        model_name: The model name (e.g., "openrouter/x-ai/grok-4")
        options: Dictionary of options (e.g., {"temperature": 0.3})

    Returns:
        ModelConfig with the appropriate variation index
    """
    models_dir = Path(__file__).parent.parent.parent / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    model_filename_base = model_name.replace("/", "-")

    # Find all existing model files for this model name
    existing_files = sorted(models_dir.glob(f"{model_filename_base}-*.yaml"))

    # Check each existing file for matching options
    for model_file in existing_files:
        try:
            yaml_obj = YAML()
            model_data = yaml_obj.load(model_file.read_text(encoding="utf-8"))
            file_options = model_data.get("options", {}) or {}

            # Compare options (normalize to handle type differences)
            if _options_match(options, file_options):
                variation_index = _extract_variation_index(model_file.stem)
                return ModelConfig(
                    name=model_name,
                    options=options,
                    variation_index=variation_index,
                )
        except Exception as e:
            print(f"Warning: Could not read model file {model_file.name}: {e}")

    # No matching file found, create a new one with next variation index
    next_index = _get_next_variation_index(existing_files)
    config = ModelConfig(name=model_name, options=options, variation_index=next_index)

    # Create the model metadata file
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


def _get_next_variation_index(existing_files: list[Path]) -> int:
    """Get the next available variation index."""
    if not existing_files:
        return 1

    max_index = 0
    for f in existing_files:
        index = _extract_variation_index(f.stem)
        max_index = max(max_index, index)

    return max_index + 1


def _create_model_file(config: ModelConfig) -> Path:
    """Create a model metadata file for the given configuration."""
    model_file_path = config.get_model_file_path()

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
        config: ModelConfig with name, options, and variation_index

    Returns:
        Path to the model metadata file
    """
    model_file_path = config.get_model_file_path()

    # If the file already exists, return its path
    if model_file_path.exists():
        return model_file_path

    # Create the model metadata file
    return _create_model_file(config)
