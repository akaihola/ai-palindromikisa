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


@pytest.fixture
def mock_models_dir(tmp_path: Path):
    """Fixture that creates a temporary models directory and patches MODELS_DIR."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    with mock.patch.object(ai_palindromikisa.models, "MODELS_DIR", models_dir):
        yield models_dir


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

    def test_default_skip_value(self):
        """Test ModelConfig skip field defaults to False."""
        config = ModelConfig(name="test/model")
        assert config.skip is False

    def test_skip_can_be_set_to_true(self):
        """Test ModelConfig skip field can be set to True."""
        config = ModelConfig(name="test/model", skip=True)
        assert config.skip is True

    def test_skip_can_be_explicitly_set_to_false(self):
        """Test ModelConfig skip field can be explicitly set to False."""
        config = ModelConfig(name="test/model", skip=False)
        assert config.skip is False

    def test_skip_with_options(self):
        """Test ModelConfig skip field works with options."""
        config = ModelConfig(
            name="test/model", options={"temperature": 0.5}, skip=True
        )
        assert config.skip is True
        assert config.options == {"temperature": 0.5}


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

    def test_reads_model_files(self, mock_models_dir):
        """Test reading model configurations from files."""
        # Create test model files with new naming convention
        (mock_models_dir / "test-model.yaml").write_text("name: test/model\n")
        (mock_models_dir / "test-model-t03.yaml").write_text(
            "name: test/model\noptions:\n  temperature: 0.3\n"
        )

        configs = get_all_model_configs()

        assert len(configs) == 2
        # Configs are sorted by filename alphabetically
        # test-model-t03.yaml comes before test-model.yaml
        assert configs[0].name == "test/model"
        assert configs[0].options == {"temperature": 0.3}
        assert configs[1].name == "test/model"
        assert configs[1].options == {}

    def test_empty_models_directory(self, mock_models_dir):
        """Test with empty models directory."""
        configs = get_all_model_configs()
        assert configs == []

    def test_skips_models_with_skip_true_by_default(self, mock_models_dir):
        """Test that models with skip=true are excluded by default."""
        (mock_models_dir / "model-included.yaml").write_text("name: test/included\n")
        (mock_models_dir / "model-skipped.yaml").write_text(
            "name: test/skipped\nskip: true\n"
        )

        configs = get_all_model_configs()

        assert len(configs) == 1
        assert configs[0].name == "test/included"
        assert configs[0].skip is False

    def test_includes_skipped_models_with_include_skipped_true(self, mock_models_dir):
        """Test that models with skip=true are included when include_skipped=True."""
        (mock_models_dir / "model-included.yaml").write_text("name: test/included\n")
        (mock_models_dir / "model-skipped.yaml").write_text(
            "name: test/skipped\nskip: true\n"
        )

        configs = get_all_model_configs(include_skipped=True)

        assert len(configs) == 2
        # Sorted alphabetically by filename
        assert configs[0].name == "test/included"
        assert configs[0].skip is False
        assert configs[1].name == "test/skipped"
        assert configs[1].skip is True

    def test_skip_defaults_to_false_in_yaml(self, mock_models_dir):
        """Test that skip field defaults to False when not in YAML file."""
        (mock_models_dir / "test-model.yaml").write_text("name: test/model\n")

        configs = get_all_model_configs()

        assert len(configs) == 1
        assert configs[0].skip is False

    def test_skip_with_options(self, mock_models_dir):
        """Test skip field works correctly with options."""
        (mock_models_dir / "skipped-with-options.yaml").write_text(
            "name: test/model\noptions:\n  temperature: 0.5\nskip: true\n"
        )

        configs = get_all_model_configs()
        assert len(configs) == 0

        configs = get_all_model_configs(include_skipped=True)
        assert len(configs) == 1
        assert configs[0].options == {"temperature": 0.5}
        assert configs[0].skip is True

    def test_multiple_models_mixed_skip_status(self, mock_models_dir):
        """Test with multiple models having mixed skip status."""
        (mock_models_dir / "model-a.yaml").write_text("name: test/a\n")
        (mock_models_dir / "model-b.yaml").write_text("name: test/b\nskip: true\n")
        (mock_models_dir / "model-c.yaml").write_text("name: test/c\nskip: false\n")
        (mock_models_dir / "model-d.yaml").write_text("name: test/d\nskip: true\n")

        # Without include_skipped, only non-skipped models
        configs = get_all_model_configs()
        assert len(configs) == 2
        names = [c.name for c in configs]
        assert "test/a" in names
        assert "test/c" in names
        assert "test/b" not in names
        assert "test/d" not in names

        # With include_skipped, all models
        configs = get_all_model_configs(include_skipped=True)
        assert len(configs) == 4
        skip_statuses = {c.name: c.skip for c in configs}
        assert skip_statuses == {
            "test/a": False,
            "test/b": True,
            "test/c": False,
            "test/d": True,
        }


class TestFindOrCreateModelConfig:
    """Tests for find_or_create_model_config function."""

    def test_finds_existing_config_without_options(self, mock_models_dir):
        """Test finding existing model config without options."""
        (mock_models_dir / "test-model.yaml").write_text("name: test/model\n")

        config = find_or_create_model_config("test/model", {})

        assert config.name == "test/model"
        assert config.options == {}

    def test_finds_existing_config_with_matching_options(self, mock_models_dir):
        """Test finding existing model config with matching options."""
        (mock_models_dir / "test-model.yaml").write_text("name: test/model\n")
        (mock_models_dir / "test-model-t03.yaml").write_text(
            "name: test/model\noptions:\n  temperature: 0.3\n"
        )

        config = find_or_create_model_config("test/model", {"temperature": 0.3})

        assert config.name == "test/model"
        assert config.options == {"temperature": 0.3}

    def test_creates_new_config_for_new_options(self, mock_models_dir):
        """Test creating new model config for new options."""
        (mock_models_dir / "test-model.yaml").write_text("name: test/model\n")

        config = find_or_create_model_config("test/model", {"temperature": 0.5})

        assert config.name == "test/model"
        assert config.options == {"temperature": 0.5}
        # Verify file was created with option suffix
        assert (mock_models_dir / "test-model-t05.yaml").exists()

    def test_creates_first_config_for_new_model_with_options(self, mock_models_dir):
        """Test creating first model config for new model with options."""
        config = find_or_create_model_config("new/model", {"temperature": 0.3})

        assert config.name == "new/model"
        assert config.options == {"temperature": 0.3}
        # Verify file was created with option suffix
        assert (mock_models_dir / "new-model-t03.yaml").exists()

    def test_creates_first_config_for_new_model_without_options(self, mock_models_dir):
        """Test creating first model config for new model without options."""
        config = find_or_create_model_config("new/model", {})

        assert config.name == "new/model"
        assert config.options == {}
        # Verify file was created without suffix
        assert (mock_models_dir / "new-model.yaml").exists()

    def test_raises_error_on_options_mismatch(self, mock_models_dir):
        """Test that ValueError is raised when file exists with different options."""
        # Create file with different options than what we'll request
        (mock_models_dir / "test-model-t03.yaml").write_text(
            "name: test/model\noptions:\n  temperature: 0.5\n"
        )

        with pytest.raises(ValueError, match="different options"):
            find_or_create_model_config("test/model", {"temperature": 0.3})


class TestLoadModelConfigFromPath:
    """Tests for load_model_config_from_path function."""

    def test_loads_config_without_options(self, mock_models_dir):
        """Test loading model config without options."""
        (mock_models_dir / "gpt-4o-mini.yaml").write_text("name: gpt-4o-mini\n")

        config = load_model_config_from_path("models/gpt-4o-mini.yaml")

        assert config is not None
        assert config.name == "gpt-4o-mini"
        assert config.options == {}

    def test_loads_config_with_options(self, mock_models_dir):
        """Test loading model config with options."""
        (mock_models_dir / "openrouter-x-ai-grok-4-t1.yaml").write_text(
            "name: openrouter/x-ai/grok-4\noptions:\n  temperature: 1.0\n"
        )

        config = load_model_config_from_path("models/openrouter-x-ai-grok-4-t1.yaml")

        assert config is not None
        assert config.name == "openrouter/x-ai/grok-4"
        assert config.options == {"temperature": 1.0}

    def test_returns_none_for_missing_file(self, mock_models_dir):
        """Test returns None when model file doesn't exist."""
        config = load_model_config_from_path("models/nonexistent.yaml")
        assert config is None

    def test_returns_none_for_invalid_yaml(self, mock_models_dir):
        """Test returns None when YAML is invalid."""
        (mock_models_dir / "invalid.yaml").write_text("invalid: yaml: content:")

        config = load_model_config_from_path("models/invalid.yaml")

        assert config is None

    def test_returns_none_for_missing_name_field(self, mock_models_dir):
        """Test returns None when name field is missing."""
        (mock_models_dir / "no-name.yaml").write_text("options:\n  temperature: 0.5\n")

        config = load_model_config_from_path("models/no-name.yaml")

        assert config is None

    def test_loads_config_with_skip_true(self, mock_models_dir):
        """Test loading model config with skip=true."""
        (mock_models_dir / "skipped-model.yaml").write_text(
            "name: test/skipped\nskip: true\n"
        )

        config = load_model_config_from_path("models/skipped-model.yaml")

        assert config is not None
        assert config.name == "test/skipped"
        assert config.skip is True

    def test_loads_config_with_skip_false(self, mock_models_dir):
        """Test loading model config with skip=false."""
        (mock_models_dir / "included-model.yaml").write_text(
            "name: test/included\nskip: false\n"
        )

        config = load_model_config_from_path("models/included-model.yaml")

        assert config is not None
        assert config.name == "test/included"
        assert config.skip is False

    def test_loads_config_with_skip_defaults_to_false(self, mock_models_dir):
        """Test loading model config where skip field is omitted defaults to false."""
        (mock_models_dir / "default-model.yaml").write_text("name: test/default\n")

        config = load_model_config_from_path("models/default-model.yaml")

        assert config is not None
        assert config.name == "test/default"
        assert config.skip is False

    def test_loads_config_with_skip_and_options(self, mock_models_dir):
        """Test loading model config with both skip and options."""
        (mock_models_dir / "skipped-with-opts.yaml").write_text(
            "name: test/model\noptions:\n  temperature: 0.7\nskip: true\n"
        )

        config = load_model_config_from_path("models/skipped-with-opts.yaml")

        assert config is not None
        assert config.name == "test/model"
        assert config.options == {"temperature": 0.7}
        assert config.skip is True


class TestGetDisplayNameFromPath:
    """Tests for get_display_name_from_path function."""

    def test_returns_display_name_without_options(self, mock_models_dir):
        """Test display name from path without options."""
        (mock_models_dir / "gpt-4o-mini.yaml").write_text("name: gpt-4o-mini\n")

        display_name = get_display_name_from_path("models/gpt-4o-mini.yaml")

        assert display_name == "gpt-4o-mini"

    def test_returns_display_name_with_options(self, mock_models_dir):
        """Test display name from path with options."""
        (mock_models_dir / "openrouter-x-ai-grok-4-t1.yaml").write_text(
            "name: openrouter/x-ai/grok-4\noptions:\n  temperature: 1.0\n"
        )

        display_name = get_display_name_from_path(
            "models/openrouter-x-ai-grok-4-t1.yaml"
        )

        assert display_name == "openrouter/x-ai/grok-4: temperature 1.0"

    def test_returns_display_name_with_multiple_options(self, mock_models_dir):
        """Test display name from path with multiple options."""
        (mock_models_dir / "test-model.yaml").write_text(
            "name: test/model\noptions:\n  temperature: 0.7\n  top_p: 0.9\n"
        )

        display_name = get_display_name_from_path("models/test-model.yaml")

        assert display_name == "test/model: temperature 0.7, top_p 0.9"

    def test_fallback_for_missing_file(self, mock_models_dir):
        """Test fallback to cleaned filename when file doesn't exist."""
        display_name = get_display_name_from_path(
            "models/openrouter-x-ai-grok-4-t1.yaml"
        )

        # Falls back to cleaned filename (without models/ prefix and .yaml suffix)
        assert display_name == "openrouter-x-ai-grok-4-t1"

    def test_fallback_for_path_without_models_prefix(self, mock_models_dir):
        """Test fallback when path doesn't have models/ prefix."""
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
    def test_fallback_parametrized(self, path, expected, mock_models_dir):
        """Test fallback behavior for various paths when files don't exist."""
        display_name = get_display_name_from_path(path)

        assert display_name == expected
