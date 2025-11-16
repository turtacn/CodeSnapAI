from typing import List
import networkx as nx

from codesage.analyzers.ast_models import FileAST, ASTNode
from codesage.analyzers.semantic.symbol_table import SymbolTable, Scope

class CallGraphBuilder:
    def __init__(self):
        self._graph = nx.DiGraph()
        self._symbol_table: SymbolTable = None

    def build(self, files: List[FileAST], symbol_table: SymbolTable) -> nx.DiGraph:
        self._symbol_table = symbol_table
        for file in files:
            self._graph.add_node(file.path)
            for func in file.functions:
                self._traverse_for_calls(func.tree, f"{file.path}::{func.name}")
            for class_node in file.classes:
                for method in class_node.methods:
                    self._traverse_for_calls(method.tree, f"{file.path}::{class_node.name}::{method.name}")
        return self._graph

    def _traverse_for_calls(self, node: ASTNode, caller_name: str):
        if node is None:
            return

        if node.node_type == 'call_expression':
            # Simplified symbol resolution
            callee_name = node.value
            callee_symbol = self._symbol_table.lookup(callee_name, Scope.MODULE) # Simplified scope
            if callee_symbol:
                self._graph.add_edge(caller_name, f"{callee_symbol.location.file}::{callee_symbol.name}")

        for child in node.children:
            self._traverse_for_calls(child, caller_name)

    def detect_recursion(self) -> List[List[str]]:
        return list(nx.simple_cycles(self._graph))

    def calculate_call_depth(self, entry_point: str) -> int:
        if not nx.is_directed_acyclic_graph(self._graph):
            return 0

        # This is not the most efficient way, but it's simple
        paths = []
        for node in self._graph.nodes():
            try:
                paths.extend(list(nx.all_simple_paths(self._graph, source=entry_point, target=node)))
            except nx.NodeNotFound:
                pass

        return max(len(p) for p in paths) if paths else 0
