from tree_sitter import Language, Parser, Node
import tree_sitter_python as tspython
from codesage.analyzers.base import BaseParser
from codesage.analyzers.ast_models import FunctionNode, ClassNode, ImportNode
from codesage.snapshot.models import ASTSummary, ComplexityMetrics
from typing import List

PY_COMPLEXITY_NODES = {
    "if_statement",
    "elif_clause",
    "for_statement",
    "while_statement",
    "try_statement",
    "with_statement",
    "match_statement",
    "case_clause",
    "except_clause",
    "return_statement",
}

class PythonParser(BaseParser):
    def __init__(self):
        super().__init__()
        py_language = Language(tspython.language())
        self.parser = Parser(py_language)

    def _parse(self, source_code: bytes):
        return self.parser.parse(source_code)

    def extract_functions(self) -> List[FunctionNode]:
        functions = []
        if not self.tree:
            return functions

        for node in self._walk(self.tree.root_node):
            if node.type in ("function_definition", "async_function_definition"):
                functions.append(self._build_function_node(node))

        return functions

    def extract_classes(self) -> List[ClassNode]:
        classes = []
        if not self.tree:
            return classes

        for node in self._walk(self.tree.root_node):
            if node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                bases_node = node.child_by_field_name("superclasses")

                methods = []
                body = node.child_by_field_name("body")
                if body:
                    for child in self._walk(body):
                        if child.type in ("function_definition", "async_function_definition"):
                            methods.append(self._build_function_node(child))

                base_classes = []
                if bases_node:
                    for child in bases_node.children:
                        if child.type == "identifier":
                            base_classes.append(self._text(child))

                classes.append(ClassNode(
                    node_type="class",
                    name=self._text(name_node) if name_node else '',
                    methods=methods,
                    base_classes=base_classes
                ))
        return classes

    def extract_imports(self) -> List[ImportNode]:
        imports = []
        if not self.tree:
            return imports

        for node in self._walk(self.tree.root_node):
            if node.type == "import_statement":
                for name in node.children:
                    if name.type == "dotted_name":
                        alias_node = name.parent.child_by_field_name('alias')
                        imports.append(ImportNode(
                            node_type="import",
                            path=self._text(name),
                            alias=self._text(alias_node) if alias_node else None,
                        ))

            if node.type == "import_from_statement":
                module_name_node = node.child_by_field_name('module_name')
                if module_name_node:
                    module_name = self._text(module_name_node)
                    for name in node.children:
                        if name.type == "dotted_name":
                            alias_node = name.parent.child_by_field_name('alias')
                            imports.append(ImportNode(
                                node_type="import",
                                path=f"{module_name}.{self._text(name)}",
                                alias=self._text(alias_node) if alias_node else None,
                                is_relative='.' in module_name
                            ))
        return imports

    def _build_function_node(self, func_node):
        name_node = func_node.child_by_field_name("name")
        params_node = func_node.child_by_field_name("parameters")
        return_type_node = func_node.child_by_field_name("return_type")

        decorators = self._get_decorators(func_node)

        is_async = False
        if func_node.type == "async_function_definition":
            is_async = True
        else:
            for child in func_node.children:
                if child.type == "async":
                    is_async = True
                    break

        return_type = None
        if return_type_node:
            type_text = self._text(return_type_node).strip()
            if type_text:
                return_type = f"-> {type_text}"

        return FunctionNode(
            node_type="function",
            name=self._text(name_node) if name_node else '',
            params=[self._text(param) for param in params_node.children] if params_node else [],
            return_type=return_type,
            start_line=func_node.start_point[0],
            end_line=func_node.end_point[0],
            complexity=self.calculate_complexity(func_node),
            is_async=is_async,
            decorators=decorators
        )

    def _get_decorators(self, func_node):
        parent = func_node.parent
        if parent is None or parent.type != "decorated_definition":
            return []

        decorators = []
        for child in parent.children:
            if child.type == "decorator":
                text = self._text(child).strip()
                if "(" in text:
                    text = text.split("(", 1)[0]
                decorators.append(text)
        return decorators

    def calculate_complexity(self, node: Node) -> int:
        complexity = 1

        for child in self._walk(node):
            if child.type in PY_COMPLEXITY_NODES:
                complexity += 1

        return complexity

    def get_ast_summary(self, source_code: str) -> ASTSummary:
        self.parse(source_code)
        return ASTSummary(
            function_count=len(self.extract_functions()),
            class_count=len(self.extract_classes()),
            import_count=len(self.extract_imports()),
            comment_lines=self._count_comment_lines()
        )

    def _count_comment_lines(self) -> int:
        if not self.tree:
            return 0

        comment_lines = set()
        for node in self._walk(self.tree.root_node):
            if node.type == 'comment':
                start_line = node.start_point[0]
                end_line = node.end_point[0]
                for i in range(start_line, end_line + 1):
                    comment_lines.add(i)
        return len(comment_lines)

    def get_complexity_metrics(self, source_code: str) -> ComplexityMetrics:
        self.parse(source_code)
        if not self.tree:
            return ComplexityMetrics(cyclomatic=0)

        return ComplexityMetrics(
            cyclomatic=self.calculate_complexity(self.tree.root_node)
        )
