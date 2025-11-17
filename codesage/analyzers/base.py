from abc import ABC, abstractmethod
from typing import List, Optional
from tree_sitter import Node, Tree
from codesage.analyzers.ast_models import FunctionNode, ImportNode
from codesage.snapshot.models import ASTSummary, ComplexityMetrics

class BaseParser(ABC):
    def __init__(self):
        self.tree: Optional[Tree] = None
        self._source: bytes = b""

    def parse(self, source_code: str):
        self._source = source_code.encode("utf8")
        self.tree = self._parse(self._source)

    @abstractmethod
    def _parse(self, source_code: bytes) -> Tree:
        raise NotImplementedError

    @abstractmethod
    def extract_functions(self) -> List[FunctionNode]:
        raise NotImplementedError

    @abstractmethod
    def extract_imports(self) -> List[ImportNode]:
        raise NotImplementedError

    def get_ast_summary(self, source_code: str) -> ASTSummary:
        self.parse(source_code)
        # Placeholder implementation
        return ASTSummary(
            function_count=len(self.extract_functions()),
            class_count=0,  # Implement in subclasses
            import_count=len(self.extract_imports()),
            comment_lines=0  # Implement in subclasses
        )

    def get_complexity_metrics(self, source_code: str) -> ComplexityMetrics:
        self.parse(source_code)
        # Placeholder implementation
        return ComplexityMetrics(cyclomatic=0)

    def _walk(self, node):
        stack = [node]
        while stack:
            n = stack.pop()
            yield n
            stack.extend(reversed(n.children))

    def _text(self, node):
        return self._source[node.start_byte:node.end_byte].decode("utf8")
