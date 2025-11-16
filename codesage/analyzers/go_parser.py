from tree_sitter import Language, Parser
import tree_sitter_go as tsgo
from typing import List

from codesage.analyzers.base import BaseParser
from codesage.analyzers.ast_models import FunctionNode, ImportNode, ClassNode


GO_COMPLEXITY_NODES = {
    "if_statement",
    "for_statement",
    "switch_statement",
    "type_switch_statement",
    "select_statement",
    "return_statement",
}

GO_CASE_NODES = {
    "case_clause",
    "default_case",
}


class GoParser(BaseParser):
    def __init__(self):
        super().__init__()
        go_language = Language(tsgo.language())
        self.parser = Parser(go_language)

    def _parse(self, source_code: bytes):
        try:
            return self.parser.parse(source_code)
        except Exception as e:
            # TODO: Add logging here
            print(f"Error parsing source code: {e}")
            return None

    # ----------------------------------------------------------------------
    # Function extraction
    # ----------------------------------------------------------------------
    def extract_functions(self) -> List[FunctionNode]:
        functions = []
        if not self.tree or not self.tree.root_node:
            return functions

        for node in self._walk(self.tree.root_node):
            if node.type in ("function_declaration", "method_declaration"):
                functions.append(self._build_function_node(node))

        return functions

    # ----------------------------------------------------------------------
    # Interface extraction
    # ----------------------------------------------------------------------
    def extract_interfaces(self) -> List[ClassNode]:
        interfaces = []
        if not self.tree:
            return interfaces

        for node in self._walk(self.tree.root_node):
            if node.type == "type_spec":
                name_node = node.child_by_field_name("name")
                type_node = node.child_by_field_name("type")
                if not (name_node and type_node and type_node.type == "interface_type"):
                    continue

                interface_name = self._text(name_node)
                methods = self._extract_interface_methods(type_node)

                interfaces.append(
                    ClassNode(
                        node_type="interface",
                        name=interface_name,
                        methods=methods,
                        base_classes=[],
                    )
                )

        return interfaces

    def _extract_interface_methods(self, interface_type_node):
        methods = []
        for child in interface_type_node.children:
            if child.type == "method_elem":
                name_node = child.child_by_field_name("name")
                if name_node is None:
                    for c in child.children:
                        if c.type in ("field_identifier", "identifier"):
                            name_node = c
                            break

                method_name = self._text(name_node) if name_node else "<anonymous>"

                methods.append(
                    FunctionNode(
                        node_type="function",
                        name=method_name,
                        params=[],
                        return_type=None,
                        start_line=child.start_point[0],
                        end_line=child.end_point[0],
                        complexity=1,
                        is_async=False,
                        decorators=[],
                    )
                )
        return methods

    # ----------------------------------------------------------------------
    # Imports
    # ----------------------------------------------------------------------
    def extract_imports(self) -> List[ImportNode]:
        imports = []
        if not self.tree or not self.tree.root_node:
            return imports

        for node in self._walk(self.tree.root_node):
            if node.type == "import_spec":
                path_node = node.child_by_field_name('path')
                alias_node = node.child_by_field_name('alias')
                imports.append(
                    ImportNode(
                        node_type="import",
                        path=self._text(path_node).strip('"') if path_node else '',
                        alias=self._text(alias_node) if alias_node else None
                    )
                )
        return imports

    # ----------------------------------------------------------------------
    # FunctionNode builder
    # ----------------------------------------------------------------------
    def _build_function_node(self, func_node):
        name_node = func_node.child_by_field_name("name")
        params_node = func_node.child_by_field_name("parameters")
        return_type_node = func_node.child_by_field_name("result")

        params = []
        if params_node:
            for param in params_node.children:
                if param.type == "parameter_declaration":
                    params.append(self._text(param))

        return FunctionNode(
            node_type="function",
            name=self._text(name_node) if name_node else '',
            params=params,
            return_type=self._text(return_type_node) if return_type_node else None,
            start_line=func_node.start_point[0],
            end_line=func_node.end_point[0],
            complexity=self.calculate_complexity(func_node),
            is_async=False,
            decorators=[]
        )

    # ----------------------------------------------------------------------
    # Cyclomatic Complexity
    # ----------------------------------------------------------------------
    def calculate_complexity(self, node) -> int:
        complexity = 1

        for child in self._walk(node):
            t = child.type
            if t in GO_COMPLEXITY_NODES:
                complexity += 1
            elif t in GO_CASE_NODES:
                complexity += 1

        return complexity
