import unittest
from codesage.analyzers.semantic.symbol_table import SymbolTable, Symbol, Scope
from codesage.analyzers.ast_models import FileAST, FunctionNode
from codesage.analyzers.semantic.models import CodeLocation

class TestSymbolTableExtended(unittest.TestCase):
    def test_symbol_tags(self):
        # Create a FunctionNode with tags
        func_node = FunctionNode(
            node_type="function",
            name="execute_query",
            tags={"db_op"},
            is_exported=True
        )

        file_ast = FileAST(
            path="db_utils.py",
            functions=[func_node]
        )

        table = SymbolTable().build_from_ast(file_ast)
        symbol = table.lookup("execute_query", Scope.MODULE)

        self.assertIsNotNone(symbol)
        self.assertIn("db_op", symbol.tags)
        self.assertTrue(symbol.is_exported)

    def test_symbol_references(self):
        # Test manually adding references
        loc = CodeLocation(file="main.py", start_line=10, end_line=10)
        symbol = Symbol("test_func", "function", loc, Scope.MODULE)

        ref_loc = CodeLocation(file="other.py", start_line=5, end_line=5)
        symbol.references.append(ref_loc)

        self.assertEqual(len(symbol.references), 1)
        self.assertEqual(symbol.references[0].file, "other.py")

if __name__ == "__main__":
    unittest.main()
