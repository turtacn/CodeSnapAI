import pytest
from pathlib import Path
import hashlib

from codesage.utils.file_utils import (
    scan_directory,
    compute_hash,
    detect_language,
)


@pytest.fixture
def test_repo(tmp_path: Path):
    """Creates a temporary directory structure for testing."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Create .gitignore
    (repo_dir / ".gitignore").write_text("*.pyc\n__pycache__/\nbuild/\n")

    # Create some files
    (repo_dir / "valid.py").write_text("print('hello')")
    (repo_dir / "ignored.pyc").write_text("binary_stuff")

    # Create a nested directory
    nested_dir = repo_dir / "src"
    nested_dir.mkdir()
    (nested_dir / "main.go").write_text("package main")
    (nested_dir / "another.py").write_text("import this")

    # Create ignored directories
    pycache_dir = repo_dir / "__pycache__"
    pycache_dir.mkdir()
    (pycache_dir / "cachefile.bin").write_text("cached")

    build_dir = nested_dir / "build"
    build_dir.mkdir()
    (build_dir / "output.o").write_text("object file")

    return repo_dir


def test_scan_directory_respects_gitignore(test_repo: Path):
    """
    Tests that scan_directory correctly filters files based on .gitignore rules.
    """
    scanned_files = scan_directory(str(test_repo))

    # Convert to relative paths for easier comparison
    relative_files = {p.relative_to(test_repo) for p in scanned_files}

    # Expected files (as Path objects)
    expected = {
        Path("valid.py"),
        Path("src/main.go"),
        Path("src/another.py"),
        Path(".gitignore"),  # gitignore files themselves are not ignored
    }

    assert relative_files == expected


def test_compute_file_hash(tmp_path: Path):
    """
    Tests the SHA-256 hash computation.
    """
    file_content = b"hello world"
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(file_content)

    expected_hash = hashlib.sha256(file_content).hexdigest()
    computed_hash = compute_hash(test_file)

    assert computed_hash == expected_hash


def test_detect_language_by_extension():
    """
    Tests the language detection based on file extensions.
    """
    assert detect_language(Path("test.go")) == "go"
    assert detect_language(Path("main.py")) == "python"
    assert detect_language(Path("archive.zip")) == "unknown"
    assert detect_language(Path("Makefile")) == "unknown"
    assert (
        detect_language(Path("component.tsx")) == "unknown"
    )  # Based on current implementation
    assert detect_language(Path("header.h")) == "c"
