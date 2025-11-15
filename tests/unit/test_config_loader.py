import pytest
from pathlib import Path
import yaml
from unittest.mock import patch

from codesage.config.loader import load_config, deep_merge
from codesage.config.defaults import DEFAULT_CONFIG


@pytest.fixture
def mock_home_dir(tmp_path: Path):
    """Mocks the home directory to isolate global config tests."""
    home_dir = tmp_path / "home" / "user"
    home_dir.mkdir(parents=True)
    return home_dir


@pytest.fixture
def project_dir(tmp_path: Path):
    """Creates a temporary project directory."""
    proj_dir = tmp_path / "my_project"
    proj_dir.mkdir()
    return proj_dir


def test_load_default_config(project_dir, mock_home_dir):
    """Tests loading config when no global or project files exist."""
    with patch("pathlib.Path.home", return_value=mock_home_dir):
        config = load_config(str(project_dir))
        assert config == DEFAULT_CONFIG


def test_merge_project_config(project_dir, mock_home_dir):
    """Tests that project config correctly overrides global and default configs."""
    # 1. Setup global config
    global_config_dir = mock_home_dir / ".codesage"
    global_config_dir.mkdir()
    global_config_path = global_config_dir / "config.yaml"
    global_config_content = {
        "thresholds": {"complexity": 10},
        "ignore_paths": ["global_ignore/"],
    }
    global_config_path.write_text(yaml.dump(global_config_content))

    # 2. Setup project config
    project_config_path = project_dir / ".codesage.yaml"
    project_config_content = {
        "thresholds": {"complexity": 15, "duplication": 5},
        "languages": {"python": {"extensions": [".py", ".pyw"]}},
    }
    project_config_path.write_text(yaml.dump(project_config_content))

    with patch("pathlib.Path.home", return_value=mock_home_dir):
        config = load_config(str(project_dir))

    # 3. Assertions
    assert config["thresholds"]["complexity"] == 15  # Project overrides global
    assert config["thresholds"]["duplication"] == 5  # Project overrides default
    assert config["ignore_paths"] == ["global_ignore/"]  # Global overrides default
    assert config["languages"]["python"]["extensions"] == [
        ".py",
        ".pyw",
    ]  # Project overrides default


def test_invalid_yaml_raises_error(project_dir, mock_home_dir):
    """Tests that a malformed YAML file raises a ValueError."""
    project_config_path = project_dir / ".codesage.yaml"
    project_config_path.write_text("thresholds: [1, 2,")  # Invalid YAML syntax

    with patch("pathlib.Path.home", return_value=mock_home_dir):
        with pytest.raises(ValueError, match="Error parsing project config file"):
            load_config(str(project_dir))


def test_deep_merge_logic():
    """Tests the deep_merge utility function."""
    base = {"a": 1, "b": {"c": 2, "d": [3, 4]}}
    override = {"b": {"c": 5, "e": 6}, "f": 7}

    merged = deep_merge(base, override)

    expected = {
        "a": 1,
        "b": {"c": 5, "d": [3, 4], "e": 6},  # overridden  # preserved  # added
        "f": 7,  # added
    }
    assert merged == expected
