from tree_sitter import Language, Parser, Node
import tree_sitter_python as tspython
from codesage.analyzers.base import BaseParser
from codesage.analyzers.ast_models import FunctionNode, ClassNode, ImportNode, VariableNode
from codesage.snapshot.models import ASTSummary, ComplexityMetrics
from typing import List, Set

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

SEMANTIC_TAGS_RULES = {
    "execute": "db_op",
    "fetchone": "db_op",
    "fetchall": "db_op",
    "commit": "db_op",
    "rollback": "db_op",
    "connect": "network",
    "socket": "network",
    "send": "network",
    "recv": "network",
    "get": "network",  # requests.get
    "post": "network", # requests.post
    "open": "file_io",
    "read": "file_io",
    "write": "file_io",
    "print": "io_op",
    "input": "io_op",
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
                # Check if the function is inside a class
                parent = node.parent
                while parent:
                    if parent.type == "class_definition":
                        break
                    parent = parent.parent
                else:
                    functions.append(self._build_function_node(node))

        return functions

    def extract_classes(self) -> List[ClassNode]:
        classes = []
        if not self.tree:
            return classes

        for node in self._walk(self.tree.root_node):
            if node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                name = self._text(name_node) if name_node else ''
                bases_node = node.child_by_field_name("superclasses")

                methods = []
                fields = []
                body = node.child_by_field_name("body")
                if body:
                    # Capture class attributes (fields) first
                    for child in body.children:
                        assignment = None
                        # Check for direct assignment or wrapped in expression_statement
                        if child.type in ("assignment", "annotated_assignment"):
                             assignment = child
                        elif child.type == "expression_statement":
                            child_node = child.child(0)
                            if child_node.type in ("assignment", "annotated_assignment"):
                                assignment = child_node

                        if assignment:
                            left = assignment.child_by_field_name("left")
                            if left and left.type == "identifier":
                                field_name = self._text(left)
                                type_name = None
                                if assignment.type == "annotated_assignment":
                                    type_node = assignment.child_by_field_name("type")
                                    if type_node:
                                        type_name = self._text(type_node)
                                    else:
                                        # Fallback to index based access: left, type, value
                                        # 0: left, 1: :, 2: type, 3: =, 4: value
                                        # Try named child index 1 (0 is left, 1 is type, 2 is value)
                                        if assignment.named_child_count > 1:
                                            type_node = assignment.named_child(1)
                                            if type_node:
                                                type_name = self._text(type_node)
                                elif assignment.type == "assignment":
                                    # Regular assignment doesn't have type
                                    pass

                                # For annotated assignment, right side is "value", for assignment it is "right"
                                right = assignment.child_by_field_name("value")
                                if not right:
                                    right = assignment.child_by_field_name("right")
                                value = self._text(right) if right else None
                                if value and len(value) > 30:
                                    value = value[:30] + "..."

                                fields.append(VariableNode(
                                    node_type="variable",
                                    name=field_name,
                                    value=value,
                                    kind="field",
                                    type_name=type_name,
                                    is_exported=not field_name.startswith("_"),
                                    start_line=child.start_point[0],
                                    end_line=child.end_point[0]
                                ))
                        elif child.type in ("function_definition", "async_function_definition"):
                            methods.append(self._build_function_node(child))

                base_classes = []
                if bases_node:
                    for child in bases_node.children:
                        if child.type == "identifier":
                            base_classes.append(self._text(child))

                is_exported = not name.startswith("_")

                classes.append(ClassNode(
                    node_type="class",
                    name=name,
                    methods=methods,
                    fields=fields,
                    base_classes=base_classes,
                    is_exported=is_exported
                ))
        return classes

    def extract_imports(self) -> List[ImportNode]:
        imports = []
        if not self.tree:
            return imports

        for node in self._walk(self.tree.root_node):
            if node.type == "import_statement":
                for child in node.children:
                    # In import_statement, we want dotted_name or aliased_import
                    if child.type == "dotted_name":
                        imports.append(ImportNode(
                            node_type="import",
                            path=self._text(child),
                            alias=None,
                            lineno=node.start_point[0] + 1
                        ))
                    elif child.type == "aliased_import":
                        name_node = child.child_by_field_name("name")
                        alias_node = child.child_by_field_name("alias")
                        imports.append(ImportNode(
                            node_type="import",
                            path=self._text(name_node),
                            alias=self._text(alias_node),
                            lineno=node.start_point[0] + 1
                        ))

            if node.type == "import_from_statement":
                module_name_node = node.child_by_field_name('module_name')
                if module_name_node:
                    module_name = self._text(module_name_node)
                    # Iterate children to find imported names, excluding module_name
                    for child in node.children:
                        # Avoid reprocessing module_name if it is a dotted_name
                        if child == module_name_node:
                            continue

                        if child.type == "dotted_name":
                            imports.append(ImportNode(
                                node_type="import",
                                path=f"{module_name}.{self._text(child)}",
                                alias=None,
                                is_relative='.' in module_name,
                                lineno=node.start_point[0] + 1
                            ))
                        elif child.type == "aliased_import":
                            name_node = child.child_by_field_name("name")
                            alias_node = child.child_by_field_name("alias")
                            imports.append(ImportNode(
                                node_type="import",
                                path=f"{module_name}.{self._text(name_node)}",
                                alias=self._text(alias_node),
                                is_relative='.' in module_name,
                                lineno=node.start_point[0] + 1
                            ))
        return imports

    def extract_variables(self) -> List[VariableNode]:
        variables = []
        if not self.tree:
            return variables

        # Scan for global assignment nodes
        for node in self._walk(self.tree.root_node):
            # We are looking for top-level assignments
            if node.type == "expression_statement":
                assignment = node.child(0)
                if assignment.type in ("assignment", "annotated_assignment"):
                    # Ensure it is top-level (global)
                    # Parent of expression_statement should be module
                    if node.parent and node.parent.type == "module":
                        left = assignment.child_by_field_name("left")
                        if left and left.type == "identifier":
                            name = self._text(left)

                            type_name = None
                            if assignment.type == "annotated_assignment":
                                type_node = assignment.child_by_field_name("type")
                                if type_node:
                                    type_name = self._text(type_node)

                            # Extract value (simplified)
                            right = assignment.child_by_field_name("right")
                            value = self._text(right) if right else None

                            is_exported = not name.startswith("_")

                            variables.append(VariableNode(
                                node_type="variable",
                                name=name,
                                value=value,
                                kind="global",
                                type_name=type_name,
                                is_exported=is_exported,
                                start_line=node.start_point[0],
                                end_line=node.end_point[0]
                            ))
        return variables

    def _build_function_node(self, func_node):
        name_node = func_node.child_by_field_name("name")
        name = self._text(name_node) if name_node else ''
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

        # Analyze function body for tags
        tags = self._extract_tags(func_node)

        is_exported = not name.startswith("_")

        return FunctionNode(
            node_type="function",
            name=name,
            params=[self._text(param) for param in params_node.children] if params_node else [],
            return_type=return_type,
            start_line=func_node.start_point[0],
            end_line=func_node.end_point[0],
            complexity=self.calculate_complexity(func_node),
            is_async=is_async,
            decorators=decorators,
            tags=tags,
            is_exported=is_exported
        )

    def _extract_tags(self, node: Node) -> Set[str]:
        tags = set()
        for child in self._walk(node):
            if child.type == "call":
                function_node = child.child_by_field_name("function")
                if function_node:
                    # Handle object.method() calls
                    if function_node.type == "attribute":
                        attribute_node = function_node.child_by_field_name("attribute")
                        if attribute_node:
                            method_name = self._text(attribute_node)
                            if method_name in SEMANTIC_TAGS_RULES:
                                tags.add(SEMANTIC_TAGS_RULES[method_name])
                    # Handle direct function calls e.g. print()
                    elif function_node.type == "identifier":
                        func_name = self._text(function_node)
                        if func_name in SEMANTIC_TAGS_RULES:
                            tags.add(SEMANTIC_TAGS_RULES[func_name])
        return tags

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
