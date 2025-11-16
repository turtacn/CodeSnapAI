import pytest
from codesage.snapshot.markdown_generator import MarkdownGenerator
from codesage.snapshot.models import ProjectSnapshot
import pathlib

# Sample analysis results for testing the generate method
def get_analysis_results(tmp_path):
    return [
        {
            "path": str(tmp_path / "src/main.py"),
            "language": "python",
        "hash": "abc",
        "lines": 100,
        "ast_summary": {
            "function_count": 5, "class_count": 1, "import_count": 10, "comment_lines": 15
        },
        "complexity_metrics": {"cyclomatic": 12},
        "detected_patterns": [],
        "issues": [],
    }
]

@pytest.fixture
def markdown_generator():
    """Provides a MarkdownGenerator instance."""
    return MarkdownGenerator(template_dir="codesage/snapshot/templates")

@pytest.fixture(autouse=True)
def create_dummy_file(tmp_path):
    """Creates a dummy file for tests to use."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").touch()

@pytest.fixture
def generated_snapshot(markdown_generator, tmp_path):
    """Provides a ProjectSnapshot generated from sample analysis results."""
    return markdown_generator.generate(get_analysis_results(tmp_path), {})

def test_generate_snapshot(generated_snapshot, tmp_path):
    """Tests that the generate method creates a valid ProjectSnapshot."""
    assert isinstance(generated_snapshot, ProjectSnapshot)
    assert len(generated_snapshot.files) == 1
    assert generated_snapshot.files[0].path == str(tmp_path / "src/main.py")

def test_render_overview_section(markdown_generator, generated_snapshot):
    """Tests that the project overview section is rendered correctly."""
    report = markdown_generator.render(generated_snapshot, "default_report.md.jinja2")
    assert "Total Files" in report
    assert "Total Lines of Code" in report

def test_render_complexity_section(markdown_generator, generated_snapshot):
    """Tests that the complexity section is rendered with functions."""
    report = markdown_generator.render(generated_snapshot, "default_report.md.jinja2")
    assert "## 🔥 Complexity Hotspots" in report
    # The dummy data in the generator should produce function entries
    assert "function_4" in report

def test_render_dependency_graph(markdown_generator, generated_snapshot):
    """Tests that the Mermaid.js dependency graph is rendered."""
    report = markdown_generator.render(generated_snapshot, "default_report.md.jinja2")
    assert "```mermaid" in report
    assert "No dependencies found" in report # Since the graph is empty

def test_code_highlighting(markdown_generator):
    """Tests that code blocks are correctly highlighted with Pygments."""
    code = "def hello():\n    print('Hello, World!')"
    language = "python"
    highlighted_code = markdown_generator._highlight_code(code, language)
    assert "\x1b[" in highlighted_code  # Check for ANSI escape codes
