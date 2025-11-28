"""Tests for model configuration handling."""

from pathlib import Path
from unittest import mock

import pytest

import ai_palindromikisa.models
from ai_palindromikisa.models import (
    ModelConfig,
    _options_match,
    find_or_create_model_config,
    get_all_model_configs,
    get_display_name_from_path,
    load_model_config_from_path,
)


class TestModelConfig:
    """Tests for ModelConfig dataclass."""

    def test_default_values(self):
        """Test ModelConfig default values."""
        config = ModelConfig(name="test/model")
        assert config.name == "test/model"
        assert config.options == {}

    def test_get_base_filename_no_options(self):
        """Test base filename generation without options."""
        config = ModelConfig(name="openrouter/x-ai/grok-4")
        assert config.get_base_filename() == "openrouter-x-ai-grok-4"

    def test_get_base_filename_with_options(self):
        """Test base filename generation with options."""
        config = ModelConfig(
            name="openrouter/x-ai/grok-4", options={"temperature": 0.3}
        )
        assert config.get_base_filename() == "openrouter-x-ai-grok-4-t03"

    def test_get_display_name_no_options(self):
        """Test display name generation without options."""
        config = ModelConfig(name="openrouter/x-ai/grok-4")
        assert config.get_display_name() == "openrouter/x-ai/grok-4"

    def test_get_display_name_with_single_option(self):
        """Test display name generation with single option."""
        config = ModelConfig(
            name="openrouter/x-ai/grok-4", options={"temperature": 1.0}
        )
        assert config.get_display_name() == "openrouter/x-ai/grok-4: temperature 1.0"

    def test_get_display_name_with_multiple_options(self):
        """Test display name generation with multiple options (sorted)."""
        config = ModelConfig(
            name="gpt-4o-mini", options={"temperature": 0.3, "top_p": 0.9}
        )
        assert config.get_display_name() == "gpt-4o-mini: temperature 0.3, top_p 0.9"

    @pytest.mark.parametrize(
        "name,options,expected",
        [
            ("gpt-4o-mini", {}, "gpt-4o-mini"),
            ("openrouter/x-ai/grok-4", {}, "openrouter/x-ai/grok-4"),
            (
                "openrouter/x-ai/grok-4",
                {"temperature": 1.0},
                "openrouter/x-ai/grok-4: temperature 1.0",
            ),
            (
                "openrouter/anthropic/claude-opus-4.5",
                {"temperature": 0.5},
                "openrouter/anthropic/claude-opus-4.5: temperature 0.5",
            ),
            (
                "test/model",
                {"max_tokens": 1000, "temperature": 0.7},
                "test/model: max_tokens 1000, temperature 0.7",
            ),
        ],
    )
    def test_get_display_name_parametrized(self, name, options, expected):
        """Test display name for various model names and options."""
        config = ModelConfig(name=name, options=options)
        assert config.get_display_name() == expected

    @pytest.mark.parametrize(
        "name,options,expected",
        [
            ("test/model", {}, "test-model"),
            ("gemini/gemini-2.0-flash", {}, "gemini-gemini-2.0-flash"),
            (
                "openrouter/x-ai/grok-4",
                {"temperature": 0.3},
                "openrouter-x-ai-grok-4-t03",
            ),
            (
                "openrouter/x-ai/grok-4",
                {"temperature": 1.0},
                "openrouter-x-ai-grok-4-t1",
            ),
            (
                "test/model",
                {"temperature": 0.3, "top_p": 0.9},
                "test-model-t03-tp09",
            ),
        ],
    )
    def test_get_base_filename_parametrized(self, name, options, expected):
        """Test base filename for various model names and options."""
        config = ModelConfig(name=name, options=options)
        assert config.get_base_filename() == expected


class TestOptionsMatch:
    """Tests for _options_match function."""

    @pytest.mark.parametrize(
        "opts1,opts2,expected",
        [
            # Exact matches
            ({}, {}, True),
            ({"temperature": 0.3}, {"temperature": 0.3}, True),
            ({"a": 1, "b": 2}, {"a": 1, "b": 2}, True),
            # Numeric type differences (should match)
            ({"temperature": 0.3}, {"temperature": 0.30}, True),
            ({"count": 5}, {"count": 5.0}, True),
            # Different values
            ({"temperature": 0.3}, {"temperature": 0.5}, False),
            # Different keys
            ({"temperature": 0.3}, {"temp": 0.3}, False),
            ({"a": 1}, {"a": 1, "b": 2}, False),
            # None handling
            (None, {}, True),
            ({}, None, True),
            (None, None, True),
        ],
    )
    def test_options_match(self, opts1, opts2, expected):
        """Test option dictionary matching."""
        assert _options_match(opts1, opts2) == expected


class TestGetAllModelConfigs:
    """Tests for get_all_model_configs function."""

    def test_reads_model_files(self, tmp_path: Path):
        """Test reading model configurations from files."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        # Create test model files with new naming convention
        (models_dir / "test-model.yaml").write_text("name: test/model\n")
        (models_dir / "test-model-t03.yaml").write_text(
            "name: test/model\noptions:\n  temperature: 0.3\n"
        )

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            configs = get_all_model_configs()

        assert len(configs) == 2
        # Configs are sorted by filename alphabetically
        # test-model-t03.yaml comes before test-model.yaml
        assert configs[0].name == "test/model"
        assert configs[0].options == {"temperature": 0.3}
        assert configs[1].name == "test/model"
        assert configs[1].options == {}

    def test_empty_models_directory(self, tmp_path: Path):
        """Test with empty models directory."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            configs = get_all_model_configs()

        assert configs == []


class TestFindOrCreateModelConfig:
    """Tests for find_or_create_model_config function."""

    def test_finds_existing_config_without_options(self, tmp_path: Path):
        """Test finding existing model config without options."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "test-model.yaml").write_text("name: test/model\n")

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            config = find_or_create_model_config("test/model", {})

        assert config.name == "test/model"
        assert config.options == {}

    def test_finds_existing_config_with_matching_options(self, tmp_path: Path):
        """Test finding existing model config with matching options."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "test-model.yaml").write_text("name: test/model\n")
        (models_dir / "test-model-t03.yaml").write_text(
            "name: test/model\noptions:\n  temperature: 0.3\n"
        )

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            config = find_or_create_model_config("test/model", {"temperature": 0.3})

        assert config.name == "test/model"
        assert config.options == {"temperature": 0.3}

    def test_creates_new_config_for_new_options(self, tmp_path: Path):
        """Test creating new model config for new options."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "test-model.yaml").write_text("name: test/model\n")

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            config = find_or_create_model_config("test/model", {"temperature": 0.5})

        assert config.name == "test/model"
        assert config.options == {"temperature": 0.5}
        # Verify file was created with option suffix
        assert (models_dir / "test-model-t05.yaml").exists()

    def test_creates_first_config_for_new_model_with_options(self, tmp_path: Path):
        """Test creating first model config for new model with options."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            config = find_or_create_model_config("new/model", {"temperature": 0.3})

        assert config.name == "new/model"
        assert config.options == {"temperature": 0.3}
        # Verify file was created with option suffix
        assert (models_dir / "new-model-t03.yaml").exists()

    def test_creates_first_config_for_new_model_without_options(self, tmp_path: Path):
        """Test creating first model config for new model without options."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            config = find_or_create_model_config("new/model", {})

        assert config.name == "new/model"
        assert config.options == {}
        # Verify file was created without suffix
        assert (models_dir / "new-model.yaml").exists()

    def test_raises_error_on_options_mismatch(self, tmp_path: Path):
        """Test that ValueError is raised when file exists with different options."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        # Create file with different options than what we'll request
        (models_dir / "test-model-t03.yaml").write_text(
            "name: test/model\noptions:\n  temperature: 0.5\n"
        )

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            with pytest.raises(ValueError, match="different options"):
                find_or_create_model_config("test/model", {"temperature": 0.3})


class TestLoadModelConfigFromPath:
    """Tests for load_model_config_from_path function."""

    def test_loads_config_without_options(self, tmp_path: Path):
        """Test loading model config without options."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "gpt-4o-mini.yaml").write_text("name: gpt-4o-mini\n")

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            config = load_model_config_from_path("models/gpt-4o-mini.yaml")

        assert config is not None
        assert config.name == "gpt-4o-mini"
        assert config.options == {}

    def test_loads_config_with_options(self, tmp_path: Path):
        """Test loading model config with options."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "openrouter-x-ai-grok-4-t1.yaml").write_text(
            "name: openrouter/x-ai/grok-4\noptions:\n  temperature: 1.0\n"
        )

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            config = load_model_config_from_path(
                "models/openrouter-x-ai-grok-4-t1.yaml"
            )

        assert config is not None
        assert config.name == "openrouter/x-ai/grok-4"
        assert config.options == {"temperature": 1.0}

    def test_returns_none_for_missing_file(self, tmp_path: Path):
        """Test returns None when model file doesn't exist."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            config = load_model_config_from_path("models/nonexistent.yaml")

        assert config is None

    def test_returns_none_for_invalid_yaml(self, tmp_path: Path):
        """Test returns None when YAML is invalid."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "invalid.yaml").write_text("invalid: yaml: content:")

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            config = load_model_config_from_path("models/invalid.yaml")

        assert config is None

    def test_returns_none_for_missing_name_field(self, tmp_path: Path):
        """Test returns None when name field is missing."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "no-name.yaml").write_text("options:\n  temperature: 0.5\n")

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            config = load_model_config_from_path("models/no-name.yaml")

        assert config is None


class TestGetDisplayNameFromPath:
    """Tests for get_display_name_from_path function."""

    def test_returns_display_name_without_options(self, tmp_path: Path):
        """Test display name from path without options."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "gpt-4o-mini.yaml").write_text("name: gpt-4o-mini\n")

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            display_name = get_display_name_from_path("models/gpt-4o-mini.yaml")

        assert display_name == "gpt-4o-mini"

    def test_returns_display_name_with_options(self, tmp_path: Path):
        """Test display name from path with options."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "openrouter-x-ai-grok-4-t1.yaml").write_text(
            "name: openrouter/x-ai/grok-4\noptions:\n  temperature: 1.0\n"
        )

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            display_name = get_display_name_from_path(
                "models/openrouter-x-ai-grok-4-t1.yaml"
            )

        assert display_name == "openrouter/x-ai/grok-4: temperature 1.0"

    def test_returns_display_name_with_multiple_options(self, tmp_path: Path):
        """Test display name from path with multiple options."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "test-model.yaml").write_text(
            "name: test/model\noptions:\n  temperature: 0.7\n  top_p: 0.9\n"
        )

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            display_name = get_display_name_from_path("models/test-model.yaml")

        assert display_name == "test/model: temperature 0.7, top_p 0.9"

    def test_fallback_for_missing_file(self, tmp_path: Path):
        """Test fallback to cleaned filename when file doesn't exist."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            display_name = get_display_name_from_path(
                "models/openrouter-x-ai-grok-4-t1.yaml"
            )

        # Falls back to cleaned filename (without models/ prefix and .yaml suffix)
        assert display_name == "openrouter-x-ai-grok-4-t1"

    def test_fallback_for_path_without_models_prefix(self, tmp_path: Path):
        """Test fallback when path doesn't have models/ prefix."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            display_name = get_display_name_from_path("some-model.yaml")

        assert display_name == "some-model"

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("models/gpt-4o-mini.yaml", "gpt-4o-mini"),
            ("models/test-model-t03.yaml", "test-model-t03"),
            ("unknown-model.yaml", "unknown-model"),
            ("path/to/model.yaml", "path/to/model"),
        ],
    )
    def test_fallback_parametrized(self, path, expected, tmp_path: Path):
        """Test fallback behavior for various paths when files don't exist."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            display_name = get_display_name_from_path(path)

        assert display_name == expected
