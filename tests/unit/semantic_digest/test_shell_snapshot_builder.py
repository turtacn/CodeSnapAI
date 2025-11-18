from pathlib import Path
import pytest
from codesage.semantic_digest.shell_snapshot_builder import ShellSemanticSnapshotBuilder, SnapshotConfig

@pytest.fixture
def shell_project_path(tmp_path: Path):
    shell_dir = tmp_path / "scripts"
    shell_dir.mkdir()
    (shell_dir / "script.sh").write_text(
        """
        #!/bin/bash

        # This is a comment
        echo "Hello, World!"

        function my_func() {
            ls -l
        }

        my_func
        curl "http://example.com"
        """
    )
    (shell_dir / "no_extension").write_text(
        """#!/usr/bin/env bash
        grep "foo" "bar.txt"
        """
    )
    (tmp_path / "not_shell.txt").write_text("This is not a shell file.")
    return tmp_path

def test_shell_builder_collects_shell_files(shell_project_path: Path):
    builder = ShellSemanticSnapshotBuilder(shell_project_path, SnapshotConfig())
    snapshot = builder.build()
    assert len(snapshot.files) == 2
    paths = {f.path for f in snapshot.files}
    assert "scripts/script.sh" in paths
    assert "scripts/no_extension" in paths

def test_shell_builder_basic_metrics(shell_project_path: Path):
    builder = ShellSemanticSnapshotBuilder(shell_project_path, SnapshotConfig())
    snapshot = builder.build()
    script_sh = next(f for f in snapshot.files if f.path == "scripts/script.sh")
    no_extension = next(f for f in snapshot.files if f.path == "scripts/no_extension")

    assert script_sh.metrics.lines_of_code > 0
    assert script_sh.metrics.num_functions == 1
    assert no_extension.metrics.num_functions == 0

def test_shell_builder_external_commands(shell_project_path: Path):
    builder = ShellSemanticSnapshotBuilder(shell_project_path, SnapshotConfig())
    snapshot = builder.build()
    script_sh = next(f for f in snapshot.files if f.path == "scripts/script.sh")
    assert "echo" in script_sh.symbols["external_commands"]
    assert "ls" in script_sh.symbols["external_commands"]
    assert "curl" in script_sh.symbols["external_commands"]

    no_extension = next(f for f in snapshot.files if f.path == "scripts/no_extension")
    assert "grep" in no_extension.symbols["external_commands"]
