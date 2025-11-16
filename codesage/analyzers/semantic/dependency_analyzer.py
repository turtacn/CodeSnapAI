from typing import List, Dict, Tuple
import networkx as nx
import sys

from codesage.analyzers.ast_models import FileAST, ImportNode
from codesage.analyzers.semantic.base_analyzer import SemanticAnalyzer, AnalysisContext
from codesage.analyzers.semantic.models import DependencyGraph

class DependencyAnalyzer(SemanticAnalyzer[List[ImportNode]]):
    def analyze(self, file_ast: FileAST, context: AnalysisContext) -> List[ImportNode]:
        return file_ast.imports

    def analyze_project(self, files: List[FileAST]) -> DependencyGraph:
        graph = self._build_import_graph(files)
        cycles = self._detect_cycles(graph)
        max_depth = self._calculate_max_depth(graph)

        return DependencyGraph(
            nodes=list(graph.nodes),
            edges=list(graph.edges),
            cycles=cycles,
            max_depth=max_depth
        )

    def _build_import_graph(self, files: List[FileAST]) -> nx.DiGraph:
        graph = nx.DiGraph()
        for file in files:
            graph.add_node(file.path)
            for imp in file.imports:
                # Simplified import resolution
                graph.add_edge(file.path, imp.path)
        return graph

    def _detect_cycles(self, graph: nx.DiGraph) -> List[List[str]]:
        return list(nx.simple_cycles(graph))

    def _calculate_max_depth(self, graph: nx.DiGraph) -> int:
        if not nx.is_directed_acyclic_graph(graph):
            # Cannot calculate longest path in a cyclic graph
            return 0

        try:
            return len(nx.dag_longest_path(graph))
        except nx.NetworkXUnfeasible:
            # This can happen in graphs with no paths
            return 0


    def _classify_dependencies(self, imports: List[ImportNode]) -> Dict[str, str]:
        classifications = {}
        stdlib_names = set(sys.stdlib_module_names)
        for imp in imports:
            if imp.path in stdlib_names:
                classifications[imp.path] = "stdlib"
            elif "github.com" in imp.path: # Simplified check for external libs
                classifications[imp.path] = "external"
            else:
                classifications[imp.path] = "local"
        return classifications
