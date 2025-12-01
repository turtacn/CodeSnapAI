
import os
import shutil
import subprocess
import sys
import yaml
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from codesage.cli.main import main
from codesage.utils.file_utils import read_yaml_file as load_yaml

# Mark all tests in this file as 'e2e'
pytestmark = pytest.mark.e2e

@pytest.fixture(scope="module")
def runner():
    return CliRunner()

@pytest.fixture(scope="module")
def setup_projects(tmpdir_factory):
    """Creates temporary Python and Go projects for testing."""
    base_dir = Path(str(tmpdir_factory.mktemp("projects")))

    # Python Project
    py_project_dir = base_dir / "py_project"
    py_project_dir.mkdir()
    (py_project_dir / "main.py").write_text(
        "class MyClass:\n"
        "    def method(self, arg1):\n"
        "        return arg1 * 2\n\n"
        "def top_level_func(a, b):\n"
        "    return a + b\n"
    )

    # Go Project
    go_project_dir = base_dir / "go_project"
    go_project_dir.mkdir()
    (go_project_dir / "main.go").write_text(
        "package main\n\n"
        "import \"fmt\"\n\n"
        "type Greeter struct {\n"
        "    Name string\n"
        "}\n\n"
        "func (g *Greeter) Greet() {\n"
        "    fmt.Println(\"Hello,\", g.Name)\n"
        "}\n\n"
        "func main() {\n"
        "    g := Greeter{Name: \"World\"}\n"
        "    g.Greet()\n"
        "}\n"
    )

    return base_dir, py_project_dir, go_project_dir


def run_standalone_script(script_path: Path, project_dir: Path) -> dict:
    """
    Helper to run the original snapshot scripts. These scripts write their
    output to a file instead of stdout.
    """
    script_abs = script_path.resolve()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())

    # The scripts generate predictable output filenames in the CWD
    if "py-semantic" in script_abs.name:
        output_filename = "python_semantic_digest.yaml"
        command = [sys.executable, str(script_abs), str(project_dir)]
    elif "go-semantic" in script_abs.name:
        output_filename = "go_digest.yaml"
        command = [sys.executable, str(script_abs), str(project_dir)]
    else:
        raise ValueError(f"Unknown script type: {script_abs.name}")

    output_filepath = Path.cwd() / output_filename
    if output_filepath.exists():
        output_filepath.unlink()

    subprocess.run(
        command,
        capture_output=True, # Still capture to see logs if needed
        text=True,
        check=True,
        cwd=Path.cwd(),
    )

    if not output_filepath.exists():
        raise FileNotFoundError(f"Script {script_abs.name} did not generate {output_filename}")

    with open(output_filepath, "r", encoding="utf-8") as f:
        if "py-semantic" in script_path.name:
            data = yaml.unsafe_load(f)
        else:
            data = yaml.safe_load(f)

    # Clean up the generated file
    output_filepath.unlink()

    return data


@pytest.mark.parametrize("output_format", ["yaml", "json"])
def test_python_snapshot_consistency(runner: CliRunner, setup_projects, output_format):
    """Verify codesage 'py' format matches the original Python script."""
    base_dir, py_project_dir, _ = setup_projects
    script_path = Path("semantic-snapshot/py-semantic-snapshot-v3.py")

    # 1. Run standalone script
    expected_output = run_standalone_script(script_path, py_project_dir)

    # 2. Run codesage
    output_file = base_dir / f"codesage_py_output.{output_format}"
    result = runner.invoke(
        main,
        [
            "snapshot", "create",
            str(py_project_dir),
            "--format", output_format,
            "--language", "python",
            "--output", str(output_file)
        ],
        catch_exceptions=False
    )
    assert result.exit_code == 0
    assert output_file.exists()

    if output_format == "yaml":
        codesage_output = load_yaml(output_file)
    else:
        with open(output_file, "r", encoding="utf-8") as f:
            codesage_output = json.load(f)

    # 3. Compare outputs
    assert codesage_output == expected_output


@pytest.mark.parametrize("output_format", ["yaml", "json"])
def test_go_snapshot_consistency(runner: CliRunner, setup_projects, output_format):
    """Verify codesage 'go' format matches the original Go script."""
    base_dir, _, go_project_dir = setup_projects
    script_path = Path("semantic-snapshot/go-semantic-snapshot-v4.py")

    # 1. Run standalone script
    expected_output = run_standalone_script(script_path, go_project_dir)

    # 2. Run codesage
    output_file = base_dir / f"codesage_go_output.{output_format}"
    result = runner.invoke(
        main,
        [
            "snapshot", "create",
            str(go_project_dir),
            "--format", output_format,
            "--language", "go",
            "--output", str(output_file)
        ],
        catch_exceptions=False
    )
    assert result.exit_code == 0
    assert output_file.exists()

    if output_format == "yaml":
        codesage_output = load_yaml(output_file)
    else:
        with open(output_file, "r", encoding="utf-8") as f:
            codesage_output = json.load(f)

    # 3. Compare outputs
    # Normalize for comparison - e.g., rounding floats if necessary
    if "pkgs" in codesage_output and "main" in codesage_output["pkgs"]:
        codesage_output["pkgs"]["main"]["cx_avg"] = round(codesage_output["pkgs"]["main"]["cx_avg"])
    if "pkgs" in expected_output and "main" in expected_output["pkgs"]:
         expected_output["pkgs"]["main"]["cx_avg"] = round(expected_output["pkgs"]["main"]["cx_avg"])

    # Check key structures
    assert codesage_output["root"] == expected_output["root"]
    assert "main" in codesage_output["pkgs"]
    assert "main" in expected_output["pkgs"]
    assert codesage_output["pkgs"]["main"]["files"] == expected_output["pkgs"]["main"]["files"]

    # Check for specific semantic details
    main_pkg_contents = codesage_output["pkgs"]["main"]["contents"][0]
    assert "st" in main_pkg_contents, "Structs ('st') not found in Go snapshot"
    assert len(main_pkg_contents["st"]) > 0, "No structs found in Go snapshot"
    assert main_pkg_contents["st"][0]["n"] == "Greeter", "Greeter struct not found"

    assert "fn" in main_pkg_contents, "Functions ('fn') not found in Go snapshot"
    assert len(main_pkg_contents["fn"]) > 0, "No functions found in Go snapshot"
    assert main_pkg_contents["fn"][0]["n"] == "main", "main function not found"

    assert "md" in main_pkg_contents, "Methods ('md') not found in Go snapshot"
    assert "Greeter" in main_pkg_contents["md"], "Methods for Greeter struct not found"
    assert len(main_pkg_contents["md"]["Greeter"]) > 0, "No methods found for Greeter struct"
    assert main_pkg_contents["md"]["Greeter"][0]["n"] == "Greet", "Greet method not found"


def test_original_snapshot_creation_for_other_languages(runner: CliRunner, tmp_path):
    """Test that the original snapshot mechanism is used for non-Python/Go languages."""
    java_project_dir = tmp_path / "java_project"
    java_project_dir.mkdir()
    (java_project_dir / "Main.java").write_text("class Main {}")

    os.chdir(tmp_path)

    result = runner.invoke(
        main,
        ["snapshot", "create", str(java_project_dir), "--language", "java"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    snapshot_dir = tmp_path / ".codesage" / "snapshots" / java_project_dir.name
    assert snapshot_dir.exists()

    json_files = list(snapshot_dir.glob("v*.json"))
    assert len(json_files) > 0, "No versioned JSON snapshot file was created"


def test_snapshot_show_and_cleanup(runner: CliRunner, setup_projects, tmp_path):
    """Test 'snapshot show' and 'snapshot cleanup' commands."""
    _, py_project_dir, _ = setup_projects
    project_name = py_project_dir.name

    os.chdir(tmp_path)

    # 1. Create a few snapshots using the original mechanism
    for _ in range(3):
        res = runner.invoke(
            main,
            ["snapshot", "create", str(py_project_dir), "--project", project_name, "--language", "shell"], # Use a non-py/go language
            catch_exceptions=False,
        )
        assert res.exit_code == 0

    snapshot_dir = tmp_path / ".codesage" / "snapshots" / project_name
    snapshots = [p for p in snapshot_dir.glob("v*.json")]
    assert len(snapshots) == 3

    # 2. Test 'snapshot show'
    result = runner.invoke(
        main,
        ["snapshot", "show", "--project", project_name, snapshots[0].stem],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert project_name in result.output
    assert snapshots[0].stem in result.output

    # 3. Test 'snapshot cleanup'
    result = runner.invoke(
        main,
        ["snapshot", "cleanup", "--project", project_name, "--keep", "1"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    remaining_snapshots = [p for p in snapshot_dir.glob("v*.json")]
    assert len(remaining_snapshots) == 1

    os.chdir(Path.cwd())
