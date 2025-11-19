from pathlib import Path
import yaml
from .dsl_models import PolicySet
from pydantic import ValidationError

def load_policy(path: Path) -> PolicySet:
    """Loads a policy file from the given path."""
    if not path.exists():
        raise FileNotFoundError(f"Policy file not found at: {path}")

    content = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        raw_data = yaml.safe_load(content)
    elif path.suffix == ".toml":
        try:
            import tomli
        except ImportError:
            raise ImportError("Please install 'tomli' to parse TOML policy files.")
        raw_data = tomli.loads(content)
    else:
        raise ValueError(f"Unsupported policy file format: {path.suffix}")

    try:
        return PolicySet.model_validate(raw_data)
    except ValidationError as e:
        raise ValueError(f"Invalid policy file: {e}")
