from abc import ABC, abstractmethod
from typing import Dict, Any, Set, TypeVar, Generic
from dataclasses import dataclass

from codesage.analyzers.ast_models import FileAST
from codesage.analyzers.semantic.symbol_table import SymbolTable

T = TypeVar('T')

@dataclass
class AnalysisContext:
    symbol_table: SymbolTable
    config: Dict[str, Any]
    analyzed_files: Set[str]

class SemanticAnalyzer(ABC, Generic[T]):
    @abstractmethod
    def analyze(self, file_ast: FileAST, context: AnalysisContext) -> T:
        ...
