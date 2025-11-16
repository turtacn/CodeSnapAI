import unittest
import networkx as nx

from codesage.analyzers.ast_models import FileAST, ImportNode
from codesage.analyzers.semantic.dependency_analyzer import DependencyAnalyzer

class TestDependencyAnalyzer(unittest.TestCase):

    def test_build_dependency_graph(self):
        analyzer = DependencyAnalyzer()
        files = [
            FileAST(path="a.py", imports=[ImportNode(node_type="import_statement", path="b")]),
            FileAST(path="b.py", imports=[ImportNode(node_type="import_statement", path="c")]),
            FileAST(path="c.py", imports=[]),
        ]
        graph = analyzer._build_import_graph(files)
        self.assertTrue(graph.has_edge("a.py", "b"))
        self.assertTrue(graph.has_edge("b.py", "c"))

    def test_detect_circular_dependency(self):
        analyzer = DependencyAnalyzer()
        graph = nx.DiGraph()
        graph.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")])
        cycles = analyzer._detect_cycles(graph)
        self.assertEqual(len(cycles), 1)

    def test_calculate_dependency_depth(self):
        analyzer = DependencyAnalyzer()
        graph = nx.DiGraph()
        graph.add_edges_from([("a", "b"), ("b", "c"), ("c", "d")])
        self.assertEqual(analyzer._calculate_max_depth(graph), 4)

if __name__ == '__main__':
    unittest.main()
