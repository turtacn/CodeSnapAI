from tree_sitter import Language, Parser, Node
import tree_sitter_java as tsjava
from codesage.analyzers.base import BaseParser
from codesage.analyzers.ast_models import FunctionNode, ClassNode, ImportNode, VariableNode
from codesage.snapshot.models import ASTSummary, ComplexityMetrics
from typing import List, Set

JAVA_COMPLEXITY_NODES = {
    "if_statement",
    "for_statement",
    "enhanced_for_statement",
    "while_statement",
    "do_statement",
    "switch_expression",
    "catch_clause",
    "throw_statement",
    "return_statement",
    "conditional_expression", # ternary
    "case_label", # switch case
}

SEMANTIC_TAGS_RULES = {
    "execute": "db_op",
    "executeQuery": "db_op",
    "executeUpdate": "db_op",
    "save": "db_op",
    "delete": "db_op",
    "findById": "db_op",
    "persist": "db_op",
    "merge": "db_op",

    "send": "network",
    "connect": "network",
    "openStream": "network",

    "read": "file_io",
    "write": "file_io",
    "readAllBytes": "file_io",
    "lines": "file_io",

    "println": "io_op",
    "print": "io_op",
    "readLine": "io_op",
}

ANNOTATION_TAGS = {
    "GetMapping": "network",
    "PostMapping": "network",
    "PutMapping": "network",
    "DeleteMapping": "network",
    "RequestMapping": "network",
    "PatchMapping": "network",
    "Entity": "db_op",
    "Table": "db_op",
    "Repository": "db_op",
    "Service": "service",
    "Controller": "controller",
    "RestController": "controller",
    "Component": "component",
    "Configuration": "config",
    "Bean": "config",
}

class JavaParser(BaseParser):
    def __init__(self):
        super().__init__()
        try:
            java_language = Language(tsjava.language())
            self.parser = Parser(java_language)
        except Exception as e:
            # Fallback or error handling if needed, but for now let it crash if dependencies are wrong
            raise e

    def _parse(self, source_code: bytes):
        return self.parser.parse(source_code)

    def extract_functions(self) -> List[FunctionNode]:
        functions = []
        if not self.tree:
            return functions

        for node in self._walk(self.tree.root_node):
            if node.type in ("method_declaration", "constructor_declaration"):
                # Skip lambda expressions which might be misidentified
                if self._is_lambda_expression(node):
                    continue
                functions.append(self._build_function_node(node))

        return functions
    
    def _is_lambda_expression(self, node) -> bool:
        """Check if a node is part of a lambda expression"""
        parent = node.parent
        while parent:
            if parent.type == "lambda_expression":
                return True
            parent = parent.parent
        return False

    def extract_classes(self) -> List[ClassNode]:
        classes = []
        if not self.tree:
            return classes

        for node in self._walk(self.tree.root_node):
            if node.type in ("class_declaration", "interface_declaration", "record_declaration", "enum_declaration"):
                name_node = node.child_by_field_name("name")
                name = self._text(name_node) if name_node else ''

                methods = []
                body = node.child_by_field_name("body")
                if body:
                    for child in body.children:
                        if child.type in ("method_declaration", "constructor_declaration"):
                            methods.append(self._build_function_node(child))

                base_classes = []
                # Superclass
                superclass = node.child_by_field_name("superclass")
                if superclass:
                    # The superclass node covers 'extends BaseClass', we just want 'BaseClass'
                    # It usually contains a type_identifier or generic_type
                    for child in superclass.children:
                        if child.type in ("type_identifier", "generic_type", "scoped_identifier"):
                             base_classes.append(self._text(child))

                # Interfaces
                interfaces = node.child_by_field_name("interfaces")
                if interfaces:
                    # (interfaces (type_list (type_identifier)...))
                    for child in self._walk(interfaces):
                         if child.type in ("type_identifier", "generic_type", "scoped_identifier"):
                             base_classes.append(self._text(child))

                # Check modifiers for public/private
                modifiers_node = node.child_by_field_name("modifiers")
                is_exported = False # Default package private
                tags = set()
                if modifiers_node:
                    for child in modifiers_node.children:
                        if child.type == "public" or child.type == "protected":
                             is_exported = True
                        # If no modifier, it's package-private, which is sort of exported to package.
                        # But typically 'public' is what we consider exported in libraries.
                        # Let's stick to public/protected as exported.

                    # Extract class annotations
                    decorators = self._get_annotations(modifiers_node)
                    for ann in decorators:
                        ann_name = ann.replace("@", "").split("(")[0]
                        if ann_name in ANNOTATION_TAGS:
                            tags.add(ANNOTATION_TAGS[ann_name])

                classes.append(ClassNode(
                    node_type="class",
                    name=name,
                    methods=methods,
                    base_classes=base_classes,
                    is_exported=is_exported,
                    tags=tags
                ))
        return classes

    def extract_package(self) -> str:
        if not self.tree:
            return ""

        for node in self._walk(self.tree.root_node):
            if node.type == "package_declaration":
                # (package_declaration (scoped_identifier) ...)
                for child in node.children:
                    if child.type in ("dotted_name", "scoped_identifier", "identifier"):
                        return self._text(child)
        return ""

    def extract_imports(self) -> List[ImportNode]:
        imports = []
        if not self.tree:
            return imports

        for node in self._walk(self.tree.root_node):
            if node.type == "import_declaration":
                # import_declaration usually contains dotted_name
                # (import_declaration (dotted_name) @name)
                # or (import_declaration (scoped_identifier) ...) for static imports
                # tree-sitter-java:
                # (import_declaration (identifier)) ??
                # Let's inspect children.

                path = ""
                static_import = False
                for child in node.children:
                    if child.type == "static":
                        static_import = True
                    if child.type in ("dotted_name", "scoped_identifier", "identifier"):
                        path = self._text(child)

                # Check for wildcard .*
                if self._text(node).strip().endswith(".*"):
                    path += ".*" # Rough approximation if not captured in path

                imports.append(ImportNode(
                    node_type="import",
                    path=path,
                    alias=None, # Java doesn't do 'as' aliases in imports
                    is_relative=False
                ))
        return imports

    # Java doesn't have standalone global variables in the same way Python does,
    # they are usually static fields in classes. We could extract those if needed,
    # but BaseParser doesn't mandate extract_variables (it's in PythonParser).
    # I'll skip it unless required. The plan mentioned extract_classes, extract_functions, extract_imports.

    def _build_function_node(self, func_node):
        name_node = func_node.child_by_field_name("name")
        name = self._text(name_node) if name_node else ''
        
        # Check if this is a record constructor
        is_record_constructor = False
        record_components = []
        if func_node.type == "constructor_declaration":
            parent = func_node.parent
            while parent:
                if parent.type == "record_declaration":
                    is_record_constructor = True
                    # Extract record components
                    params_list = parent.child_by_field_name("parameters")
                    if params_list:
                        for param in params_list.children:
                            if param.type == "formal_parameter":
                                record_components.append(self._text(param))
                    break
                parent = parent.parent

        params_node = func_node.child_by_field_name("parameters")
        return_type_node = func_node.child_by_field_name("type") # return type

        modifiers_node = func_node.child_by_field_name("modifiers")
        decorators = self._get_annotations(modifiers_node)
        
        # Extract throws clause
        throws_clause = []
        throws_node = func_node.child_by_field_name("throws")
        if throws_node:
            for child in throws_node.children:
                if child.type in ("type_identifier", "scoped_identifier"):
                    throws_clause.append(self._text(child))

        return_type = None
        if return_type_node:
            return_type = self._text(return_type_node)
        elif func_node.type == "constructor_declaration":
            return_type = "void" # Or class name

        # Analyze function body for tags
        tags = self._extract_tags(func_node)

        # Add tags from annotations
        for ann in decorators:
            # Extract annotation name: @Override -> Override
            ann_name = ann.replace("@", "").split("(")[0]
            if ann_name in ANNOTATION_TAGS:
                tags.add(ANNOTATION_TAGS[ann_name])

        # Check modifiers for visibility and other attributes
        is_exported = False
        is_synchronized = False
        is_static = False
        if modifiers_node:
            for child in modifiers_node.children:
                if child.type == "public" or child.type == "protected":
                    is_exported = True
                elif child.type == "synchronized":
                    is_synchronized = True
                elif child.type == "static":
                    is_static = True

        func = FunctionNode(
            node_type="function",
            name=name,
            params=[self._text(param) for param in params_node.children if param.type == "formal_parameter"] if params_node else [],
            return_type=return_type,
            start_line=func_node.start_point[0],
            end_line=func_node.end_point[0],
            complexity=self.calculate_complexity(func_node),
            is_async=False, # Java threads aren't async/await syntax usually
            decorators=decorators,
            tags=tags,
            is_exported=is_exported
        )
        
        # Add Java-specific attributes
        func.is_record_constructor = is_record_constructor
        func.record_components = record_components
        func.throws_clause = throws_clause
        func.is_synchronized = is_synchronized
        func.is_static = is_static
        
        return func

    def _extract_tags(self, node: Node) -> Set[str]:
        tags = set()
        for child in self._walk(node):
            if child.type == "method_invocation":
                name_node = child.child_by_field_name("name")
                if name_node:
                    method_name = self._text(name_node)
                    if method_name in SEMANTIC_TAGS_RULES:
                        tags.add(SEMANTIC_TAGS_RULES[method_name])
        return tags

    def _get_annotations(self, modifiers_node):
        if not modifiers_node:
            return []

        annotations = []
        for child in modifiers_node.children:
            if child.type in ("marker_annotation", "annotation", "normal_annotation"):
                # Handle different annotation types including nested ones
                annotation_text = self._text(child)
                annotations.append(annotation_text)
            elif child.type == "modifiers":
                # Recursively handle nested modifiers
                nested_annotations = self._get_annotations(child)
                annotations.extend(nested_annotations)
        return annotations

    def calculate_complexity(self, node: Node) -> int:
        complexity = 1

        for child in self._walk(node):
            if child.type in JAVA_COMPLEXITY_NODES:
                complexity += 1
            elif child.type == "binary_expression":
                 operator = child.child_by_field_name("operator")
                 if operator and self._text(operator) in ("&&", "||"):
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
            if node.type in ('line_comment', 'block_comment'):
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
