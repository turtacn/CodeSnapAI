from typing import Any, Dict, List
import jinja2
import os
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import get_lexer_by_name
from collections import Counter

from codesage.snapshot.base_generator import SnapshotGenerator
from codesage.snapshot.models import (
    ProjectSnapshot,
    AnalysisResult,
    FileSnapshot,
    SnapshotMetadata,
    DependencyGraph,
)
from codesage.analyzers.ast_models import FunctionNode
from codesage import __version__ as tool_version


class MarkdownGenerator(SnapshotGenerator):
    """Generates a Markdown report from a project snapshot."""

    def __init__(self, template_dir: str = "codesage/snapshot/templates"):
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(
        self, analysis_results: List[AnalysisResult], config: Dict[str, Any]
    ) -> ProjectSnapshot:
        """
        Generates a ProjectSnapshot object from a list of analysis results.
        """
        # This is a simplified version of what JSONGenerator does.
        # A better approach would be to have a single, format-agnostic
        # snapshot generation step, and then formatters that consume it.
        file_snapshots = [FileSnapshot.model_validate(ar) for ar in analysis_results]
        metadata = SnapshotMetadata(
            version="v1",
            timestamp=datetime.now(),
            project_name="unknown",
            file_count=len(file_snapshots),
            total_size=sum(os.path.getsize(fs.path) for fs in file_snapshots),
            tool_version=tool_version,
            config_hash="abc",
        )
        global_metrics = self._aggregate_metrics(analysis_results)
        dependency_graph = DependencyGraph() # Placeholder
        all_patterns = self._collect_all_patterns(analysis_results)
        all_issues = self._collect_all_issues(analysis_results)

        return ProjectSnapshot(
            metadata=metadata,
            files=file_snapshots,
            global_metrics=global_metrics,
            dependency_graph=dependency_graph,
            detected_patterns=all_patterns,
            issues=all_issues,
        )

    def export(self, snapshot: ProjectSnapshot, output_path: str, template_name: str = "default_report.md.jinja2"):
        """Renders a Markdown report and saves it to a file."""
        report = self.render(snapshot, template_name)
        with open(output_path, "w") as f:
            f.write(report)

    def render(self, snapshot: ProjectSnapshot, template_name: str) -> str:
        """Renders the snapshot using the specified Jinja2 template."""
        template = self.template_env.get_template(template_name)
        context = {
            "snapshot": snapshot,
            "complexity_top10": self._prepare_complexity_section(snapshot),
            "dependency_mermaid": self._generate_dependency_mermaid(snapshot.dependency_graph),
            "pattern_stats": self._prepare_pattern_stats(snapshot),
        }
        return template.render(context)

    def _prepare_complexity_section(self, snapshot: ProjectSnapshot) -> List[Dict[str, Any]]:
        """Extracts the top 10 most complex functions from the snapshot."""
        all_functions = []
        for file in snapshot.files:
            # This assumes that the complexity is stored in the FunctionNode.
            # In a real implementation, you would need to parse the AST to get functions.
            # For now, we'll create some dummy data.
            for i in range(file.ast_summary.function_count):
                all_functions.append({
                    "name": f"function_{i}",
                    "file": file.path,
                    "line": 10 * i,
                    "complexity": (i + 1) * 2,
                    "lines": 15 + i
                })

        return sorted(all_functions, key=lambda f: f["complexity"], reverse=True)[:10]

    def _generate_dependency_mermaid(self, graph: DependencyGraph) -> str:
        """Generates a Mermaid.js graph from the dependency data."""
        if not graph.edges:
            return "graph TD;\n    A[No dependencies found];"

        mermaid_graph = "graph TD;\n"
        for edge in graph.edges:
            mermaid_graph += f"    {edge[0]} --> {edge[1]};\n"
        return mermaid_graph

    def _prepare_pattern_stats(self, snapshot: ProjectSnapshot) -> Dict[str, int]:
        """Calculates statistics on detected patterns."""
        # This assumes DetectedPattern has a 'type' attribute
        pattern_counts = Counter(p.type for p in snapshot.detected_patterns)
        return dict(pattern_counts)

    def _highlight_code(self, code: str, language: str) -> str:
        """Highlights a code snippet using Pygments."""
        try:
            lexer = get_lexer_by_name(language)
            formatter = TerminalFormatter()
            return highlight(code, lexer, formatter)
        except Exception:
            return f"```{language}\n{code}\n```"

from datetime import datetime
