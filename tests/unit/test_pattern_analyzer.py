import unittest

from codesage.analyzers.ast_models import FileAST, ClassNode, FunctionNode, ASTNode
from codesage.analyzers.semantic.pattern_analyzer import PatternAnalyzer
from codesage.analyzers.semantic.base_analyzer import AnalysisContext
from codesage.analyzers.semantic.symbol_table import SymbolTable

class TestPatternAnalyzer(unittest.TestCase):

    def test_detect_god_class_python(self):
        analyzer = PatternAnalyzer()
        methods = [FunctionNode(node_type="function_definition", name=f"method{i}", cyclomatic_complexity=1) for i in range(25)]
        class_node = ClassNode(node_type="class_definition", name="GodClass", methods=methods, start_line=1, end_line=30)
        file_ast = FileAST(path="test.py", classes=[class_node])
        context = AnalysisContext(symbol_table=SymbolTable(), config={"patterns": {"god_class_threshold": 20}}, analyzed_files=set())

        patterns = analyzer.analyze(file_ast, context)
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0].pattern_type, "god_class")

    def test_detect_decorator_pattern_python(self):
        # This test needs to be updated to use the rule-based system
        pass

if __name__ == '__main__':
    unittest.main()
