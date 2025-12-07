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
    
    def to_graph_format(self, file_path: str) -> dict:
        """Convert parser output to graph builder format."""
        functions = self.extract_functions()
        imports = self.extract_imports()
        
        return {
            'file_path': file_path,
            'language': getattr(self, 'language', 'unknown'),
            'source_code': self._source.decode('utf-8') if self._source else '',
            'functions': [
                {
                    'name': func.name,
                    'qualified_name': func.qualified_name,
                    'line_start': func.line_start,
                    'line_end': func.line_end,
                    'complexity': func.complexity,
                    'parameters': func.parameters,
                    'calls': func.calls,
                    'return_type': getattr(func, 'return_type', None),
                    'decorators': getattr(func, 'decorators', []),
                    'docstring': getattr(func, 'docstring', None),
                    'is_async': getattr(func, 'is_async', False),
                    'is_generator': getattr(func, 'is_generator', False)
                }
                for func in functions
            ],
            'classes': [],  # To be implemented by subclasses
            'imports': [
                {
                    'module': imp.module,
                    'name': imp.name,
                    'alias': imp.alias,
                    'type': 'import',
                    'line_number': getattr(imp, 'line_number', None)
                }
                for imp in imports
            ],
            'metrics': {
                'loc': len(self._source.decode('utf-8').splitlines()) if self._source else 0
            }
        }
