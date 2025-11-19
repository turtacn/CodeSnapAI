import hashlib
from pathlib import Path
from typing import List, Any, Dict
import yaml
import json
from gitignore_parser import parse_gitignore


def read_yaml_file(path: Path) -> Dict[str, Any]:
    """Reads a YAML file and returns its content as a dictionary."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_yaml_file(data: Dict[str, Any], path: Path) -> None:
    """Writes a dictionary to a YAML file."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, indent=2)


def read_json_file(path: Path) -> Dict[str, Any]:
    """Reads a JSON file and returns its content as a dictionary."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def scan_directory(path: str, exclude_patterns: List[str] = None) -> List[Path]:
    """
    Scans a directory recursively, filtering files based on .gitignore rules
    and exclude patterns.
    """
    base_dir = Path(path)
    gitignore_path = base_dir / ".gitignore"

    matches = None
    if gitignore_path.is_file():
        matches = parse_gitignore(str(gitignore_path), base_dir=str(base_dir))

    all_files = list(base_dir.rglob("*"))
    filtered_files = []

    for file_path in all_files:
        if not file_path.is_file():
            continue

        if matches and matches(str(file_path)):
            continue

        if exclude_patterns:
            if any(file_path.match(pattern) for pattern in exclude_patterns):
                continue

        filtered_files.append(file_path)

    return filtered_files


def compute_hash(file_path: Path) -> str:
    """
    Computes the SHA-256 hash of a file.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def detect_language(file_path: Path) -> str:
    """
    Detects the programming language of a file based on its extension.
    """
    extension_map = {
        ".py": "python",
        ".go": "go",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".js": "javascript",
        ".ts": "typescript",
        ".rs": "rust",
    }
    return extension_map.get(file_path.suffix, "unknown")
