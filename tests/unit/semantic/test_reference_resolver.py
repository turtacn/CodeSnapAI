import unittest
from codesage.analyzers.semantic.reference_resolver import ReferenceResolver
from codesage.analyzers.semantic.symbol_table import SymbolTable, Symbol, Scope
from codesage.analyzers.ast_models import FileAST, ImportNode, FunctionNode
from codesage.analyzers.semantic.models import CodeLocation

class TestReferenceResolver(unittest.TestCase):
    def setUp(self):
        # Create mock ASTs for two files:
        # lib.py: defines 'helper'
        # main.py: imports 'lib' and (conceptually) uses it

        # lib.py
        self.lib_ast = FileAST(
            path="src/lib.py",
            functions=[
                FunctionNode(node_type="function", name="helper", is_exported=True)
            ]
        )
        self.lib_table = SymbolTable().build_from_ast(self.lib_ast)

        # main.py
        self.main_ast = FileAST(
            path="src/main.py",
            imports=[
                ImportNode(node_type="import", path="src.lib", alias=None), # direct module import
                ImportNode(node_type="import", path="src.lib.helper", alias=None) # from import
            ]
        )
        self.main_table = SymbolTable().build_from_ast(self.main_ast)

        self.project_symbols = {
            "src/lib.py": self.lib_table,
            "src/main.py": self.main_table
        }

    def test_resolve_import_module(self):
        resolver = ReferenceResolver(self.project_symbols)
        resolver.resolve()

        # Check if 'src.lib' import in main.py is resolved to 'src/lib.py'
        import_symbol = self.main_table.lookup("src.lib", Scope.MODULE)
        self.assertIsNotNone(import_symbol)
        self.assertTrue(len(import_symbol.references) > 0)
        self.assertEqual(import_symbol.references[0].file, "src/lib.py")

    def test_resolve_import_symbol(self):
        resolver = ReferenceResolver(self.project_symbols)
        resolver.resolve()

        # Check if 'src.lib.helper' import in main.py is resolved to 'helper' in 'src/lib.py'
        import_symbol = self.main_table.lookup("src.lib.helper", Scope.MODULE)
        self.assertIsNotNone(import_symbol)
        self.assertTrue(len(import_symbol.references) > 0)

        target_ref = import_symbol.references[0]
        self.assertEqual(target_ref.file, "src/lib.py")

        # Check definition side: 'helper' in lib.py should have a reference back to main.py's import
        helper_symbol = self.lib_table.lookup("helper", Scope.MODULE)
        self.assertIsNotNone(helper_symbol)
        # helper_symbol.references should contain the location of the import in main.py
        found_back_ref = False
        for ref in helper_symbol.references:
            if ref.file == "src/main.py":
                found_back_ref = True
                break
        self.assertTrue(found_back_ref)

if __name__ == "__main__":
    unittest.main()
