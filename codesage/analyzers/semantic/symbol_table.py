from typing import List, Dict, Optional, Set
from enum import Enum

from codesage.analyzers.ast_models import FileAST, FunctionNode, ClassNode, ImportNode
from codesage.analyzers.semantic.models import CodeLocation

class Scope(Enum):
    GLOBAL = 1
    MODULE = 2
    CLASS = 3
    FUNCTION = 4

class Symbol:
    def __init__(self, name: str, type: str, location: CodeLocation, scope: Scope,
                 tags: Set[str] = None, references: List[CodeLocation] = None, is_exported: bool = False):
        self.name = name
        self.type = type
        self.location = location
        self.scope = scope
        self.tags = tags or set()
        self.references = references or []
        self.is_exported = is_exported

class SymbolTable:
    def __init__(self):
        self._symbols: Dict[str, List[Symbol]] = {}

    def build_from_ast(self, file_ast: FileAST) -> 'SymbolTable':
        for func in file_ast.functions:
            loc = CodeLocation(file=file_ast.path, start_line=func.start_line, end_line=func.end_line)
            self.add_symbol(Symbol(func.name, "function", loc, Scope.MODULE,
                                   tags=func.tags, is_exported=func.is_exported))
        for class_node in file_ast.classes:
            loc = CodeLocation(file=file_ast.path, start_line=class_node.start_line, end_line=class_node.end_line)
            self.add_symbol(Symbol(class_node.name, "class", loc, Scope.MODULE,
                                   tags=class_node.tags, is_exported=class_node.is_exported))
            for method in class_node.methods:
                loc = CodeLocation(file=file_ast.path, start_line=method.start_line, end_line=method.end_line)
                self.add_symbol(Symbol(method.name, "method", loc, Scope.CLASS,
                                       tags=method.tags, is_exported=method.is_exported))
        for imp in file_ast.imports:
            loc = CodeLocation(file=file_ast.path, start_line=imp.start_line, end_line=imp.end_line)
            self.add_symbol(Symbol(imp.path, "import", loc, Scope.MODULE, tags=imp.tags))

        # Also handle variables if any
        for var in file_ast.variables:
             loc = CodeLocation(file=file_ast.path, start_line=var.start_line, end_line=var.end_line)
             self.add_symbol(Symbol(var.name, "variable", loc, Scope.MODULE,
                                    tags=var.tags, is_exported=var.is_exported))

        return self

    def add_symbol(self, symbol: Symbol):
        if symbol.name not in self._symbols:
            self._symbols[symbol.name] = []
        self._symbols[symbol.name].append(symbol)

    def lookup(self, name: str, scope: Scope) -> Optional[Symbol]:
        if name in self._symbols:
            # Simplified lookup, does not yet handle scope hierarchy
            for symbol in self._symbols[name]:
                if symbol.scope == scope:
                    return symbol
        return None

    def get_all_definitions(self) -> List[Symbol]:
        all_symbols = []
        for symbols in self._symbols.values():
            all_symbols.extend(symbols)
        return all_symbols
