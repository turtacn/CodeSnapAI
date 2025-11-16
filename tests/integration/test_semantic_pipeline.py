import unittest

from codesage.analyzers.ast_models import FileAST, ClassNode, FunctionNode
from codesage.analyzers.semantic.pipeline import AnalysisPipeline
from codesage.analyzers.semantic.base_analyzer import AnalysisContext
from codesage.analyzers.semantic.symbol_table import SymbolTable

class TestSemanticPipeline(unittest.TestCase):

    def test_end_to_end_analysis_python_project(self):
        # Create a mock FileAST for the Python project
        user_service_class = ClassNode(
            node_type="class_definition",
            name="UserService",
            start_line=1,
            end_line=25,
            methods=[FunctionNode(node_type="function_definition", name=f"method{i}", start_line=i+2, end_line=i+2, cyclomatic_complexity=1) for i in range(21)]
        )
        file_ast = FileAST(
            path="services/user_service.py",
            classes=[user_service_class]
        )

        context = AnalysisContext(
            symbol_table=SymbolTable().build_from_ast(file_ast),
            config={"patterns": {"god_class_threshold": 20}},
            analyzed_files=set()
        )

        pipeline = AnalysisPipeline(context)
        result = pipeline.run(file_ast)

        self.assertEqual(result.file_path, "services/user_service.py")
        self.assertGreater(result.complexity_metrics.cyclomatic_complexity, 0)
        self.assertEqual(len(result.detected_patterns), 1)
        self.assertEqual(result.detected_patterns[0].pattern_type, "god_class")

    def test_end_to_end_analysis_go_project(self):
        # This test will be implemented once the Go parser is available
        pass

if __name__ == '__main__':
    unittest.main()
