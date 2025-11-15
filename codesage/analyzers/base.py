from abc import ABC, abstractmethod
from typing import List, Optional
from tree_sitter import Node, Tree
from codesage.analyzers.ast_models import FunctionNode, ImportNode

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

    def _walk(self, node):
        stack = [node]
        while stack:
            n = stack.pop()
            yield n
            stack.extend(reversed(n.children))

    def _text(self, node):
        return self._source[node.start_byte:node.end_byte].decode("utf8")
