"""Tests for model configuration handling."""

from pathlib import Path
from unittest import mock

import pytest

import ai_palindromikisa.models
from ai_palindromikisa.models import (
    ModelConfig,
    _extract_variation_index,
    _options_match,
    find_or_create_model_config,
    get_all_model_configs,
)


class TestModelConfig:
    """Tests for ModelConfig dataclass."""

    def test_default_values(self):
        """Test ModelConfig default values."""
        config = ModelConfig(name="test/model")
        assert config.name == "test/model"
        assert config.options == {}
        assert config.variation_index == 1

    def test_get_base_filename(self):
        """Test base filename generation."""
        config = ModelConfig(name="openrouter/x-ai/grok-4", variation_index=2)
        assert config.get_base_filename() == "openrouter-x-ai-grok-4-2"

    @pytest.mark.parametrize(
        "name,variation,expected",
        [
            ("test/model", 1, "test-model-1"),
            ("gemini/gemini-2.0-flash", 1, "gemini-gemini-2.0-flash-1"),
            ("openrouter/x-ai/grok-4", 2, "openrouter-x-ai-grok-4-2"),
        ],
    )
    def test_get_base_filename_parametrized(self, name, variation, expected):
        """Test base filename for various model names."""
        config = ModelConfig(name=name, variation_index=variation)
        assert config.get_base_filename() == expected


class TestExtractVariationIndex:
    """Tests for _extract_variation_index function."""

    @pytest.mark.parametrize(
        "filename_stem,expected",
        [
            ("test-model-1", 1),
            ("test-model-2", 2),
            ("openrouter-x-ai-grok-4-1", 1),
            ("openrouter-x-ai-grok-4-2", 2),
            ("gemini-gemini-2.0-flash-1", 1),
            # Edge cases
            ("model-without-index", 1),  # No valid index, default to 1
            ("model-abc", 1),  # Non-numeric suffix
        ],
    )
    def test_extract_variation_index(self, filename_stem, expected):
        """Test variation index extraction from filename stems."""
        assert _extract_variation_index(filename_stem) == expected


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

        # Create test model files
        (models_dir / "test-model-1.yaml").write_text("name: test/model\n")
        (models_dir / "test-model-2.yaml").write_text(
            "name: test/model\noptions:\n  temperature: 0.3\n"
        )

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            configs = get_all_model_configs()

        assert len(configs) == 2
        # Configs should be sorted by filename
        assert configs[0].name == "test/model"
        assert configs[0].variation_index == 1
        assert configs[0].options == {}
        assert configs[1].name == "test/model"
        assert configs[1].variation_index == 2
        assert configs[1].options == {"temperature": 0.3}

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
        (models_dir / "test-model-1.yaml").write_text("name: test/model\n")

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            config = find_or_create_model_config("test/model", {})

        assert config.name == "test/model"
        assert config.variation_index == 1
        assert config.options == {}

    def test_finds_existing_config_with_matching_options(self, tmp_path: Path):
        """Test finding existing model config with matching options."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "test-model-1.yaml").write_text("name: test/model\n")
        (models_dir / "test-model-2.yaml").write_text(
            "name: test/model\noptions:\n  temperature: 0.3\n"
        )

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            config = find_or_create_model_config("test/model", {"temperature": 0.3})

        assert config.name == "test/model"
        assert config.variation_index == 2
        assert config.options == {"temperature": 0.3}

    def test_creates_new_config_for_new_options(self, tmp_path: Path):
        """Test creating new model config for new options."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "test-model-1.yaml").write_text("name: test/model\n")

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            config = find_or_create_model_config("test/model", {"temperature": 0.5})

        assert config.name == "test/model"
        assert config.variation_index == 2
        assert config.options == {"temperature": 0.5}
        # Verify file was created
        assert (models_dir / "test-model-2.yaml").exists()

    def test_creates_first_config_for_new_model(self, tmp_path: Path):
        """Test creating first model config for new model."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        with mock.patch.object(
            ai_palindromikisa.models,
            "__file__",
            str(tmp_path / "src" / "ai_palindromikisa" / "models.py"),
        ):
            config = find_or_create_model_config("new/model", {"temperature": 0.3})

        assert config.name == "new/model"
        assert config.variation_index == 1
        assert config.options == {"temperature": 0.3}
        # Verify file was created
        assert (models_dir / "new-model-1.yaml").exists()
