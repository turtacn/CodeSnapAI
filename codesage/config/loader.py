import yaml
from pathlib import Path
from typing import Dict, Any
import collections.abc
from .defaults import DEFAULT_CONFIG


def deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Recursively merges two dictionaries.
    'override' values take precedence over 'base' values.
    Lists are overridden, not merged.
    """
    result = base.copy()
    for key, value in override.items():
        if (
            isinstance(value, collections.abc.Mapping)
            and key in result
            and isinstance(result[key], collections.abc.Mapping)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(project_path: str = ".") -> Dict[str, Any]:
    """
    Loads and merges configurations from default, global, and project-specific files.
    """
    # 1. Start with the default config
    config = DEFAULT_CONFIG.copy()

    # 2. Load and merge global config
    global_config_path = Path.home() / ".codesage" / "config.yaml"
    if global_config_path.is_file():
        try:
            with open(global_config_path, "r") as f:
                global_config = yaml.safe_load(f)
                if global_config:
                    config = deep_merge(config, global_config)
        except yaml.YAMLError as e:
            # Consider logging this error instead of just printing
            print(
                f"Warning: Could not parse global config file at "
                f"{global_config_path}. Error: {e}"
            )

    # 3. Load and merge project-specific config
    project_config_path = Path(project_path) / ".codesage.yaml"
    if project_config_path.is_file():
        try:
            with open(project_config_path, "r") as f:
                project_config = yaml.safe_load(f)
                if project_config:
                    config = deep_merge(config, project_config)
        except yaml.YAMLError as e:
            # Or raise a more specific exception
            raise ValueError(
                f"Error parsing project config file at {project_config_path}: {e}"
            ) from e

    # 4. Validate final config
    if "languages" not in config or "thresholds" not in config:
        raise ValueError(
            "Configuration must contain 'languages' and 'thresholds' sections."
        )

    return config
