import ast
from typing import List, NamedTuple, Optional


class FunctionComplexity(NamedTuple):
    name: str
    lineno: int
    complexity: int


class FileComplexity(NamedTuple):
    functions: List[FunctionComplexity]
    loc: int
    num_functions: int
    max_cyclomatic_complexity: int
    avg_cyclomatic_complexity: float
    high_complexity_functions: int


class ComplexityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.complexity = 1

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncWith(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_Try(self, node):
        self.complexity += len(node.handlers)
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp):
        self.complexity += len(node.values) -1
        self.generic_visit(node)

    def visit_Assert(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_comprehension(self, node):
        self.complexity += 1
        self.generic_visit(node)


def _get_function_name(node: ast.AST) -> str:
    if isinstance(node, ast.FunctionDef):
        return node.name
    elif isinstance(node, ast.AsyncFunctionDef):
        return node.name
    return "lambda"


def analyze_file_complexity(source_code: str, high_complexity_threshold: int = 10) -> Optional[FileComplexity]:
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return None

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            visitor = ComplexityVisitor()
            visitor.visit(node)
            functions.append(
                FunctionComplexity(
                    name=_get_function_name(node),
                    lineno=node.lineno,
                    complexity=visitor.complexity,
                )
            )

    loc = len(source_code.splitlines())
    num_functions = len(functions)

    if not num_functions:
        return FileComplexity(
            functions=[],
            loc=loc,
            num_functions=0,
            max_cyclomatic_complexity=0,
            avg_cyclomatic_complexity=0.0,
            high_complexity_functions=0,
        )

    max_complexity = max(f.complexity for f in functions)
    avg_complexity = sum(f.complexity for f in functions) / num_functions
    high_complexity_count = sum(1 for f in functions if f.complexity > high_complexity_threshold)

    return FileComplexity(
        functions=functions,
        loc=loc,
        num_functions=num_functions,
        max_cyclomatic_complexity=max_complexity,
        avg_cyclomatic_complexity=avg_complexity,
        high_complexity_functions=high_complexity_count,
    )
