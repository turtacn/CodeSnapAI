"""
Semantic Graph Engine for CodeSage

This package provides a unified semantic graph representation of code,
supporting multiple programming languages and storage backends.
"""

from .models.node import Node, FunctionNode, ClassNode, FileNode, ModuleNode, VariableNode
from .models.edge import Edge, CallEdge, InheritanceEdge, ImportEdge, ContainsEdge, ReferencesEdge, DefinesEdge
from .models.graph import Graph, GraphDelta
from .graph_builder import GraphBuilder
from .storage.adapter import StorageAdapter
from .query.dsl import QueryDSL
from .query.processor import QueryProcessor

__all__ = [
    'Node', 'FunctionNode', 'ClassNode', 'FileNode', 'ModuleNode', 'VariableNode',
    'Edge', 'CallEdge', 'InheritanceEdge', 'ImportEdge', 'ContainsEdge', 'ReferencesEdge', 'DefinesEdge',
    'Graph', 'GraphDelta',
    'GraphBuilder',
    'StorageAdapter',
    'QueryDSL',
    'QueryProcessor'
]