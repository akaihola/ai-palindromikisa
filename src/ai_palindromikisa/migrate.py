"""Migration script for renaming model and log files to new option-based naming."""

from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML

from ai_palindromikisa.option_suffix import generate_option_suffix
from ai_palindromikisa.paths import BENCHMARK_LOGS_DIR, MODELS_DIR


def migrate_files(dry_run: bool = False) -> None:
    """Migrate model and log files from old naming convention to new.

    Old convention: model-name-1.yaml, model-name-2.yaml (integer suffix)
    New convention: model-name.yaml, model-name-t03.yaml (option-based suffix)

    Args:
        dry_run: If True, only print what would be done without making changes
    """
    if dry_run:
        print("DRY RUN - No changes will be made\n")

    # Track model file renames for updating log references
    model_renames: dict[str, str] = {}  # old_model_ref -> new_model_ref

    # Step 1: Process model files
    print("=== Processing model files ===\n")
    if MODELS_DIR.exists():
        for model_file in sorted(MODELS_DIR.glob("*.yaml")):
            result = _process_model_file(model_file, dry_run)
            if result:
                old_ref, new_ref = result
                model_renames[old_ref] = new_ref

    # Step 2: Process log files
    print("\n=== Processing log files ===\n")
    if BENCHMARK_LOGS_DIR.exists():
        for log_file in sorted(BENCHMARK_LOGS_DIR.glob("*.yaml")):
            _process_log_file(log_file, model_renames, dry_run)

    if dry_run:
        print("\nDRY RUN complete. Run without --dry-run to apply changes.")
    else:
        print("\nMigration complete.")


def _process_model_file(model_file: Path, dry_run: bool) -> tuple[str, str] | None:
    """Process a single model file and rename if needed.

    Returns:
        Tuple of (old_model_ref, new_model_ref) if renamed, None otherwise
    """
    yaml_obj = YAML()
    yaml_obj.preserve_quotes = True

    try:
        model_data = yaml_obj.load(model_file.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  ERROR reading {model_file.name}: {e}")
        return None

    model_name = model_data.get("name", "")
    if not model_name:
        print(f"  SKIP {model_file.name}: No 'name' field")
        return None

    options = model_data.get("options", {}) or {}

    # Generate new filename
    model_filename_base = model_name.replace("/", "-")
    suffix = generate_option_suffix(options)
    new_filename = f"{model_filename_base}{suffix}.yaml"
    new_file_path = model_file.parent / new_filename

    old_model_ref = f"models/{model_file.name}"
    new_model_ref = f"models/{new_filename}"

    if model_file.name == new_filename:
        print(f"  OK {model_file.name} (no change needed)")
        return None

    if new_file_path.exists() and new_file_path != model_file:
        # Target exists - validate content matches
        try:
            existing_data = yaml_obj.load(new_file_path.read_text(encoding="utf-8"))
            if not _model_data_matches(model_data, existing_data):
                print(
                    f"  ERROR {model_file.name} -> {new_filename}: "
                    f"Target exists with different content!"
                )
                return None
            # Content matches, can safely remove old file
            print(
                f"  MERGE {model_file.name} -> {new_filename} (duplicate, removing old)"
            )
            if not dry_run:
                model_file.unlink()
            return old_model_ref, new_model_ref
        except Exception as e:
            print(f"  ERROR reading target {new_filename}: {e}")
            return None

    print(f"  RENAME {model_file.name} -> {new_filename}")
    if not dry_run:
        model_file.rename(new_file_path)

    return old_model_ref, new_model_ref


def _model_data_matches(data1: dict, data2: dict) -> bool:
    """Check if two model data dictionaries match (ignoring comments)."""
    # Compare name
    if data1.get("name") != data2.get("name"):
        return False

    # Compare options
    opts1 = data1.get("options", {}) or {}
    opts2 = data2.get("options", {}) or {}

    if set(opts1.keys()) != set(opts2.keys()):
        return False

    for key in opts1:
        v1, v2 = opts1[key], opts2[key]
        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            if float(v1) != float(v2):
                return False
        elif v1 != v2:
            return False

    return True


def _process_log_file(
    log_file: Path, model_renames: dict[str, str], dry_run: bool
) -> None:
    """Process a single log file - update model reference and rename if needed."""
    yaml_obj = YAML()
    yaml_obj.preserve_quotes = True
    yaml_obj.default_flow_style = False
    yaml_obj.allow_unicode = True
    yaml_obj.width = 4096

    try:
        log_data = yaml_obj.load(log_file.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  ERROR reading {log_file.name}: {e}")
        return

    old_model_ref = log_data.get("model", "")
    content_changed = False

    # Check if model reference needs updating
    if old_model_ref in model_renames:
        new_model_ref = model_renames[old_model_ref]
        log_data["model"] = new_model_ref
        content_changed = True
        print(f"  UPDATE {log_file.name}: model ref {old_model_ref} -> {new_model_ref}")

    # Determine new log filename based on model reference
    current_model_ref = log_data.get("model", "")
    if current_model_ref.startswith("models/") and current_model_ref.endswith(".yaml"):
        model_base = current_model_ref[7:-5]  # Remove "models/" and ".yaml"

        # Extract date from current filename
        date_prefix = log_file.name[:11]  # "YYYY-MM-DD-"
        if len(date_prefix) == 11 and date_prefix[10] == "-":
            new_log_filename = f"{date_prefix}{model_base}.yaml"
            new_log_path = log_file.parent / new_log_filename

            if log_file.name != new_log_filename:
                if new_log_path.exists() and new_log_path != log_file:
                    print(
                        f"  ERROR {log_file.name}: Target {new_log_filename} already exists"
                    )
                    return

                print(f"  RENAME {log_file.name} -> {new_log_filename}")

                if not dry_run:
                    if content_changed:
                        # Write updated content to new location
                        string_stream = StringIO()
                        yaml_obj.dump(log_data, string_stream)
                        new_log_path.write_text(
                            string_stream.getvalue(), encoding="utf-8"
                        )
                        log_file.unlink()
                    else:
                        log_file.rename(new_log_path)
                return

    # If only content changed but filename stays the same
    if content_changed and not dry_run:
        string_stream = StringIO()
        yaml_obj.dump(log_data, string_stream)
        log_file.write_text(string_stream.getvalue(), encoding="utf-8")


