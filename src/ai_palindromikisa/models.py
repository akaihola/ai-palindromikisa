from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML


def get_all_tested_models():
    """Extract model IDs from model configuration files in the models directory."""
    models_dir = Path(__file__).parent.parent.parent / "models"

    if not models_dir.exists():
        print(f"Warning: Models directory '{models_dir}' not found.")
        print("Please create the models directory and add model configuration files.")
        return []

    models = set()
    model_files_found = 0

    for model_file in models_dir.glob("*.yaml"):
        model_files_found += 1
        try:
            yaml_obj = YAML()
            model_data = yaml_obj.load(model_file.read_text(encoding="utf-8"))
            # Extract the model name from the name field
            model_name = model_data.get("name", "")
            if model_name:
                models.add(model_name)
                print(f"Found model: {model_name} (from {model_file.name})")
            else:
                print(f"Warning: No 'name' field found in {model_file.name}")
        except Exception as e:
            print(f"Warning: Could not read model file {model_file.name}: {e}")

    if model_files_found == 0:
        print("No model configuration files found in models directory.")
    elif len(models) == 0:
        print(
            f"Found {model_files_found} model files but none had valid 'name' fields."
        )

    return sorted(models)


def ensure_model_metadata_exists(model_name):
    """Ensure the model metadata file exists in the models directory.

    Creates the file if it doesn't exist, regardless of whether tasks will be executed.

    Args:
        model_name: The model name (e.g., "gemini/gemini-2.0-flash")

    Returns:
        Path to the model metadata file
    """
    # Get models directory path
    models_dir = Path(__file__).parent.parent.parent / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    # Convert model name to filename format (replace slashes with dashes)
    model_filename = model_name.replace("/", "-")
    model_file_path = models_dir / f"{model_filename}-1.yaml"

    # If the file already exists, return its path
    if model_file_path.exists():
        return model_file_path

    # Create the model metadata file with basic structure
    model_metadata = {"name": model_name}

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
