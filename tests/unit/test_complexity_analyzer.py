import unittest

from codesage.analyzers.ast_models import FileAST, FunctionNode, ASTNode
from codesage.analyzers.semantic.complexity_analyzer import ComplexityAnalyzer
from codesage.analyzers.semantic.base_analyzer import AnalysisContext
from codesage.analyzers.semantic.symbol_table import SymbolTable

class TestComplexityAnalyzer(unittest.TestCase):

    def test_calculate_cyclomatic_complexity(self):
        analyzer = ComplexityAnalyzer()
        func_node = FunctionNode(node_type="function_declaration", name="test", cyclomatic_complexity=5)
        self.assertEqual(analyzer._calculate_cyclomatic(func_node), 5)

    def test_calculate_cognitive_complexity(self):
        analyzer = ComplexityAnalyzer()
        # if (a && b) { if (c) {} }
        nested_if_ast = ASTNode(node_type='if_statement', children=[
            ASTNode(node_type='logical_expression', value='&&', children=[
                ASTNode(node_type='if_statement', children=[])
            ])
        ])
        func_node = FunctionNode(node_type="function_declaration", name="test", children=[nested_if_ast], cyclomatic_complexity=0)
        self.assertEqual(analyzer._calculate_cognitive(func_node), 4)

    def test_aggregate_file_metrics(self):
        analyzer = ComplexityAnalyzer()
        functions = [
            FunctionNode(node_type="function_declaration", name="f1", cyclomatic_complexity=5, cognitive_complexity=2),
            FunctionNode(node_type="function_declaration", name="f2", cyclomatic_complexity=10, cognitive_complexity=4),
            FunctionNode(node_type="function_declaration", name="f3", cyclomatic_complexity=15, cognitive_complexity=6),
        ]
        file_ast = FileAST(path="test.py", functions=functions)
        metrics = analyzer._aggregate_file_metrics(functions, file_ast)
        self.assertEqual(metrics.max_function_complexity, 15)
        self.assertEqual(metrics.avg_function_complexity, 10)
        self.assertEqual(metrics.cyclomatic_complexity, 30)
        self.assertEqual(metrics.cognitive_complexity, 12)


if __name__ == '__main__':
    unittest.main()
