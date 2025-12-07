from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_go as tsgo
from typing import List, Optional, Any

from codesage.analyzers.base import BaseParser
from codesage.analyzers.ast_models import FunctionNode, ImportNode, ClassNode, VariableNode
from codesage.snapshot.models import ASTSummary, ComplexityMetrics


GO_COMPLEXITY_NODES = {
    "if_statement",
    "for_statement",
    "switch_statement",
    "type_switch_statement",
    "select_statement",
    "return_statement",
    "func_literal",
}

GO_CASE_NODES = {
    "case_clause",
    "default_case",
    "comm_clause",
}


class GoParser(BaseParser):
    def __init__(self):
        super().__init__()
        go_language = Language(tsgo.language())
        self.parser = Parser(go_language)
        self.language = go_language
        self._stats = {"goroutines": 0, "channels": 0, "errors": 0}

    def _parse(self, source_code: bytes):
        try:
            return self.parser.parse(source_code)
        except Exception as e:
            print(f"Error parsing source code: {e}")
            return None

    def _get_query_cursor(self, query_scm: str) -> QueryCursor:
        query = Query(self.language, query_scm)
        return QueryCursor(query)

    def get_stats(self):
        return self._stats

    def _update_stats(self):
        if not self.tree: return

        # 1. Goroutines
        q_go = Query(self.language, "(go_statement) @go")
        cursor_go = QueryCursor(q_go)
        self._stats["goroutines"] = len(cursor_go.captures(self.tree.root_node).get('go', []))

        # 2. Channels
        # Note: operator node text is matched via literal string in query usually,
        # or we check type 'unary_expression' and verify children.
        # But `operator: "<-"` works if "<-" is anonymous node.
        # In tree-sitter-go, `<-` is indeed operator.

        q_chan_op = Query(self.language, """
        (send_statement) @send
        (unary_expression operator: "<-") @recv
        (channel_type) @chan_type
        """)
        cursor_chan = QueryCursor(q_chan_op)
        captures = cursor_chan.captures(self.tree.root_node)
        self._stats["channels"] = len(captures.get('send', [])) + len(captures.get('recv', [])) + len(captures.get('chan_type', []))

        # 3. Errors (if err != nil)
        q_err = Query(self.language, """
        (if_statement
            condition: (binary_expression
                left: (identifier) @left
                operator: "!="
                right: (nil)
            )
        ) @if_err
        (#eq? @left "err")
        """)
        cursor_err = QueryCursor(q_err)
        self._stats["errors"] = len(cursor_err.captures(self.tree.root_node).get('if_err', []))


    # ----------------------------------------------------------------------
    # Function extraction
    # ----------------------------------------------------------------------
    def extract_functions(self) -> List[FunctionNode]:
        functions = []
        if not self.tree or not self.tree.root_node:
            return functions

        self._update_stats()

        query_scm = """
        (function_declaration
            name: (identifier) @name) @func

        (method_declaration
            receiver: (parameter_list) @receiver
            name: (field_identifier) @name) @method
        """
        cursor = self._get_query_cursor(query_scm)
        matches = cursor.matches(self.tree.root_node)

        processed_nodes = set()

        for pattern_index, captures in matches:
            node = None
            if 'func' in captures:
                node = captures['func'][0]
            elif 'method' in captures:
                node = captures['method'][0]

            if node and node not in processed_nodes:
                functions.append(self._build_function_node(node))
                processed_nodes.add(node)

        return functions

    def _build_function_node(self, node):
        is_method = node.type == "method_declaration"

        name_node = node.child_by_field_name("name")
        params_node = node.child_by_field_name("parameters")
        result_node = node.child_by_field_name("result")
        type_params_node = node.child_by_field_name("type_parameters")

        receiver_str = None
        if is_method:
            receiver_node = node.child_by_field_name("receiver")
            if receiver_node:
                receiver_str = self._text(receiver_node)

        params = []
        if params_node:
            for param in params_node.children:
                if param.type in ("parameter_declaration", "variadic_parameter_declaration"):
                    params.append(self._text(param))

        return_type = None
        if result_node:
             return_type = self._text(result_node)

        # Extract type parameters for generics (Go 1.18+)
        type_parameters = []
        is_generic = type_params_node is not None
        if type_params_node:
            for param in type_params_node.children:
                if param.type == "type_parameter_declaration":
                    param_name = None
                    param_constraint = None
                    for child in param.children:
                        if child.type == "type_identifier":
                            param_name = self._text(child)
                        elif child.type in ("type_constraint", "type_term"):
                            param_constraint = self._text(child)
                    
                    if param_name:
                        type_parameters.append({
                            'name': param_name,
                            'constraint': param_constraint or 'any'
                        })

        # Determine exported
        func_name = self._text(name_node) if name_node else ''
        is_exported = func_name[0].isupper() if func_name else False

        decorators = []
        if is_generic:
            decorators.append("generic")
        if is_exported:
            decorators.append("exported")

        func = FunctionNode(
            node_type="function",
            name=func_name,
            params=params,
            return_type=return_type,
            receiver=receiver_str,
            start_line=node.start_point[0],
            end_line=node.end_point[0],
            complexity=self.calculate_complexity(node),
            is_async=False,
            decorators=decorators
        )
        
        # Add type parameters as custom attribute
        func.type_parameters = type_parameters
        
        return func

    # ----------------------------------------------------------------------
    # Struct extraction
    # ----------------------------------------------------------------------
    def extract_structs(self) -> List[ClassNode]:
        structs = []
        if not self.tree or not self.tree.root_node:
            return structs

        query_scm = """
        (type_declaration
            (type_spec
                name: (type_identifier) @name
                type: (struct_type) @struct_body
            ) @type_spec
        )
        """
        cursor = self._get_query_cursor(query_scm)
        matches = cursor.matches(self.tree.root_node)

        for _, captures in matches:
            if 'type_spec' in captures:
                node = captures['type_spec'][0]
                structs.append(self._build_struct_node(node))

        return structs

    def _build_struct_node(self, type_spec_node) -> ClassNode:
        name_node = type_spec_node.child_by_field_name("name")
        struct_type = type_spec_node.child_by_field_name("type")
        
        # Check for type parameters (generics)
        type_params_node = type_spec_node.child_by_field_name("type_parameters")
        type_parameters = []
        if type_params_node:
            for param in type_params_node.children:
                if param.type == "type_parameter_declaration":
                    param_name = None
                    param_constraint = None
                    for child in param.children:
                        if child.type == "type_identifier":
                            param_name = self._text(child)
                        elif child.type in ("type_constraint", "type_term"):
                            param_constraint = self._text(child)
                    
                    if param_name:
                        type_parameters.append({
                            'name': param_name,
                            'constraint': param_constraint or 'any'
                        })

        fields = []
        if struct_type:
            field_list = None
            for child in struct_type.children:
                if child.type == "field_declaration_list":
                    field_list = child
                    break

            if field_list:
                for child in field_list.children:
                    if child.type == "field_declaration":
                        type_node = child.child_by_field_name("type")
                        type_str = self._text(type_node) if type_node else None
                        
                        # Extract struct tags (e.g., `json:"name"`)
                        tag_str = None
                        tag_node = child.child_by_field_name("tag")
                        if tag_node:
                            tag_str = self._text(tag_node)

                        names = []
                        for sub in child.children:
                            if sub.type == "field_identifier":
                                names.append(self._text(sub))

                        if not names:
                            # Embedded field
                            if type_str:
                                # Embedded fields are usually considered exported if the type name is uppercase
                                # e.g. *Person -> Person
                                field_name_for_exported = type_str.lstrip("*")
                                is_exported_field = field_name_for_exported[0].isupper() if field_name_for_exported else False

                                field = VariableNode(
                                    node_type="variable",
                                    name=type_str,
                                    type_name=type_str,
                                    kind="embedded_field",
                                    is_exported=is_exported_field
                                )
                                if tag_str:
                                    field.struct_tag = tag_str
                                fields.append(field)
                        else:
                            for n in names:
                                is_exported_field = n[0].isupper() if n else False
                                field = VariableNode(
                                    node_type="variable",
                                    name=n,
                                    type_name=type_str,
                                    kind="field",
                                    is_exported=is_exported_field
                                )
                                if tag_str:
                                    field.struct_tag = tag_str
                                fields.append(field)

        struct = ClassNode(
            node_type="struct",
            name=self._text(name_node) if name_node else "<anonymous>",
            fields=fields,
            methods=[],
            base_classes=[]
        )
        
        # Add type parameters as custom attribute
        struct.type_parameters = type_parameters
        
        return struct

    # ----------------------------------------------------------------------
    # Interface extraction
    # ----------------------------------------------------------------------
    def extract_interfaces(self) -> List[ClassNode]:
        interfaces = []
        if not self.tree or not self.tree.root_node:
            return interfaces

        query_scm = """
        (type_declaration
            (type_spec
                name: (type_identifier) @name
                type: (interface_type) @interface_body
            ) @type_spec
        )
        """
        cursor = self._get_query_cursor(query_scm)
        matches = cursor.matches(self.tree.root_node)

        for _, captures in matches:
            if 'type_spec' in captures:
                node = captures['type_spec'][0]
                interfaces.append(self._build_interface_node(node))

        return interfaces

    def _build_interface_node(self, type_spec_node) -> ClassNode:
        name_node = type_spec_node.child_by_field_name("name")
        interface_type = type_spec_node.child_by_field_name("type")

        methods = []
        if interface_type:
            for child in interface_type.children:
                if child.type == "method_elem":
                    name_child = child.child_by_field_name("name")
                    params_child = child.child_by_field_name("parameters")
                    result_child = child.child_by_field_name("result")

                    methods.append(FunctionNode(
                        node_type="method_signature",
                        name=self._text(name_child) if name_child else "<anon>",
                        params=[self._text(params_child)] if params_child else [],
                        return_type=self._text(result_child) if result_child else None
                    ))

        return ClassNode(
            node_type="interface",
            name=self._text(name_node) if name_node else "<anonymous>",
            methods=methods,
            base_classes=[]
        )

    # ----------------------------------------------------------------------
    # Imports
    # ----------------------------------------------------------------------
    def extract_imports(self) -> List[ImportNode]:
        imports = []
        if not self.tree or not self.tree.root_node:
            return imports

        query_scm = """
        (import_spec
            name: (package_identifier)? @alias
            path: (interpreted_string_literal) @path
        ) @import
        """
        cursor = self._get_query_cursor(query_scm)
        matches = cursor.matches(self.tree.root_node)

        processed_nodes = set()

        for _, captures in matches:
            if 'import' in captures:
                node = captures['import'][0]
                if node in processed_nodes:
                    continue
                processed_nodes.add(node)

                path_node = node.child_by_field_name('path')
                alias_node = node.child_by_field_name('name')

                imports.append(
                    ImportNode(
                        node_type="import",
                        path=self._text(path_node).strip('"') if path_node else '',
                        alias=self._text(alias_node) if alias_node else None
                    )
                )
        return imports

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
            elif t == "binary_expression":
                 op = child.child_by_field_name("operator")
                 if op and self._text(op) in ("&&", "||"):
                     complexity += 1

        return complexity

    def get_ast_summary(self, source_code: str) -> ASTSummary:
        self.parse(source_code)
        structs = self.extract_structs()
        interfaces = self.extract_interfaces()

        return ASTSummary(
            function_count=len(self.extract_functions()),
            class_count=len(structs) + len(interfaces),
            import_count=len(self.extract_imports()),
            comment_lines=self._count_comment_lines()
        )

    def _count_comment_lines(self) -> int:
        if not self.tree:
            return 0

        query_scm = "(comment) @comment"
        cursor = self._get_query_cursor(query_scm)
        captures_dict = cursor.captures(self.tree.root_node)

        comment_lines = set()
        if 'comment' in captures_dict:
            for node in captures_dict['comment']:
                start_line = node.start_point[0]
                end_line = node.end_point[0]
                for i in range(start_line, end_line + 1):
                    comment_lines.add(i)
        return len(comment_lines)
