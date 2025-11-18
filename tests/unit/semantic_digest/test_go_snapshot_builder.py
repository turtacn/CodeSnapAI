from pathlib import Path
import pytest
from codesage.semantic_digest.go_snapshot_builder import GoSemanticSnapshotBuilder, SnapshotConfig

@pytest.fixture
def go_project_path(tmp_path: Path):
    go_dir = tmp_path / "go_src"
    go_dir.mkdir()
    (go_dir / "main.go").write_text(
        """
        package main

        import (
            "fmt"
            "net/http"
        )

        type Greeter struct {
            Name string
        }

        func main() {
            fmt.Println("Hello, World!")
        }

        func greet(g Greeter) {
            fmt.Printf("Hello, %s!", g.Name)
        }
        """
    )
    (go_dir / "other.go").write_text(
        """
        package main

        // This is a comment
        func anotherFunction() {

        }
        """
    )
    (tmp_path / "not_go.txt").write_text("This is not a go file.")
    return tmp_path

def test_go_builder_collects_go_files(go_project_path: Path):
    builder = GoSemanticSnapshotBuilder(go_project_path, SnapshotConfig())
    snapshot = builder.build()
    assert len(snapshot.files) == 2
    paths = {f.path for f in snapshot.files}
    assert "go_src/main.go" in paths
    assert "go_src/other.go" in paths

def test_go_builder_basic_metrics(go_project_path: Path):
    builder = GoSemanticSnapshotBuilder(go_project_path, SnapshotConfig())
    snapshot = builder.build()
    main_go = next(f for f in snapshot.files if f.path == "go_src/main.go")
    other_go = next(f for f in snapshot.files if f.path == "go_src/other.go")

    assert main_go.metrics.lines_of_code > 0
    assert main_go.metrics.num_functions == 2
    assert main_go.metrics.num_types == 1
    assert other_go.metrics.num_functions == 1

def test_go_builder_imports_parsing(go_project_path: Path):
    builder = GoSemanticSnapshotBuilder(go_project_path, SnapshotConfig())
    snapshot = builder.build()
    main_go = next(f for f in snapshot.files if f.path == "go_src/main.go")
    assert "fmt" in main_go.symbols["imports"]
    assert "net/http" in main_go.symbols["imports"]
