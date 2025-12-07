"""
Unit tests for GraphBuilder.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch

from codesage.graph.graph_builder import GraphBuilder
from codesage.graph.models.node import FunctionNode, ClassNode, FileNode, ModuleNode
from codesage.graph.models.edge import CallEdge, InheritanceEdge, ImportEdge, ContainsEdge


class TestGraphBuilder:
    """Test GraphBuilder class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.builder = GraphBuilder()
    
    def test_init_with_schema(self):
        """Test GraphBuilder initialization with schema."""
        # Test with non-existent schema path
        builder = GraphBuilder(schema_path="/non/existent/path")
        assert builder.schema is not None  # Should use minimal schema
    
    def test_from_parser_output_python(self):
        """Test building graph from Python parser output."""
        parser_output = {
            'file_path': '/test/example.py',
            'language': 'python',
            'metrics': {'loc': 50},
            'functions': [
                {
                    'name': 'func1',
                    'qualified_name': 'example.func1',
                    'line_start': 1,
                    'line_end': 10,
                    'complexity': 3,
                    'parameters': ['arg1', 'arg2'],
                    'calls': [
                        {'name': 'func2', 'line': 5},
                        {'name': 'print', 'line': 7}
                    ]
                },
                {
                    'name': 'func2',
                    'qualified_name': 'example.func2',
                    'line_start': 11,
                    'line_end': 20,
                    'complexity': 1,
                    'parameters': [],
                    'calls': []
                }
            ],
            'classes': [
                {
                    'name': 'TestClass',
                    'qualified_name': 'example.TestClass',
                    'line_start': 21,
                    'line_end': 40,
                    'base_classes': ['BaseClass'],
                    'methods': [
                        {'name': 'method1'},
                        {'name': 'method2'}
                    ]
                }
            ],
            'imports': [
                {
                    'module': 'os',
                    'type': 'import',
                    'line_number': 1
                },
                {
                    'module': 'sys',
                    'name': 'sys',
                    'type': 'import',
                    'alias': 'system',
                    'line_number': 2
                }
            ]
        }
        
        graph = self.builder.from_parser_output(parser_output)
        
        # Check file node
        file_nodes = graph.get_nodes_by_type('file')
        assert len(file_nodes) == 1
        file_node = file_nodes[0]
        assert file_node.path == '/test/example.py'
        assert file_node.language == 'python'
        assert file_node.loc == 50
        
        # Check function nodes
        function_nodes = graph.get_nodes_by_type('function')
        assert len(function_nodes) == 2
        
        func1 = next(f for f in function_nodes if f.name == 'func1')
        assert func1.qualified_name == 'example.func1'
        assert func1.complexity == 3
        assert func1.params == ['arg1', 'arg2']
        
        func2 = next(f for f in function_nodes if f.name == 'func2')
        assert func2.qualified_name == 'example.func2'
        assert func2.complexity == 1
        
        # Check class nodes
        class_nodes = graph.get_nodes_by_type('class')
        assert len(class_nodes) == 1
        class_node = class_nodes[0]
        assert class_node.name == 'TestClass'
        assert class_node.base_classes == ['BaseClass']
        assert class_node.methods == ['method1', 'method2']
        
        # Check module nodes
        module_nodes = graph.get_nodes_by_type('module')
        assert len(module_nodes) >= 2  # os, sys modules
        
        # Check contains edges (file -> functions/classes)
        contains_edges = graph.get_edges_by_type('contains')
        assert len(contains_edges) >= 3  # file contains 2 functions + 1 class
        
        # Check call edges
        call_edges = graph.get_edges_by_type('calls')
        assert len(call_edges) >= 1  # func1 calls func2
        
        # Check import edges
        import_edges = graph.get_edges_by_type('imports')
        assert len(import_edges) >= 2  # imports os, sys
    
    def test_from_parser_output_go(self):
        """Test building graph from Go parser output."""
        parser_output = {
            'file_path': '/test/example.go',
            'language': 'go',
            'metrics': {'loc': 30},
            'functions': [
                {
                    'name': 'main',
                    'qualified_name': 'main.main',
                    'line_start': 5,
                    'line_end': 15,
                    'complexity': 2,
                    'parameters': [],
                    'calls': [
                        {'name': 'fmt.Println', 'line': 8},
                        {'name': 'helper', 'line': 10}
                    ]
                },
                {
                    'name': 'helper',
                    'qualified_name': 'main.helper',
                    'line_start': 17,
                    'line_end': 25,
                    'complexity': 1,
                    'parameters': ['input string'],
                    'calls': []
                }
            ],
            'classes': [],  # Go doesn't have classes
            'imports': [
                {
                    'module': 'fmt',
                    'type': 'import',
                    'line_number': 3
                }
            ]
        }
        
        graph = self.builder.from_parser_output(parser_output)
        
        # Check file node
        file_nodes = graph.get_nodes_by_type('file')
        assert len(file_nodes) == 1
        file_node = file_nodes[0]
        assert file_node.language == 'go'
        
        # Check function nodes
        function_nodes = graph.get_nodes_by_type('function')
        assert len(function_nodes) == 2
        
        main_func = next(f for f in function_nodes if f.name == 'main')
        assert main_func.qualified_name == 'main.main'
        
        helper_func = next(f for f in function_nodes if f.name == 'helper')
        assert helper_func.params == ['input string']
        
        # Check call edges
        call_edges = graph.get_edges_by_type('calls')
        assert len(call_edges) >= 1  # main calls helper
    
    def test_resolve_call_target_local(self):
        """Test call target resolution for local functions."""
        func_lookup = {
            'func1': 'function:/test/file.py:func1',
            'func2': 'function:/test/file.py:func2'
        }
        
        # Test local function resolution
        target = self.builder._resolve_call_target('func1', func_lookup, '/test/file.py')
        assert target == 'function:/test/file.py:func1'
        
        # Test builtin function resolution
        target = self.builder._resolve_call_target('print', func_lookup, '/test/file.py')
        assert target == 'function:builtin.print'
        
        # Test unknown function resolution
        target = self.builder._resolve_call_target('unknown_func', func_lookup, '/test/file.py')
        assert target == 'function:external.unknown_func'
    
    def test_create_function_nodes(self):
        """Test function node creation."""
        parser_output = {
            'functions': [
                {
                    'name': 'test_func',
                    'qualified_name': 'module.test_func',
                    'line_start': 1,
                    'line_end': 10,
                    'complexity': 5,
                    'parameters': ['arg1', 'arg2'],
                    'return_type': 'str',
                    'decorators': ['@property'],
                    'docstring': 'Test function',
                    'is_async': True,
                    'is_generator': False
                }
            ]
        }
        
        function_nodes = self.builder._create_function_nodes(parser_output, '/test/file.py')
        
        assert len(function_nodes) == 1
        func_node = function_nodes[0]
        assert func_node.name == 'test_func'
        assert func_node.complexity == 5
        assert func_node.params == ['arg1', 'arg2']
        assert func_node.return_type == 'str'
        assert func_node.properties['decorators'] == ['@property']
        assert func_node.properties['docstring'] == 'Test function'
        assert func_node.properties['is_async'] is True
        assert func_node.properties['is_generator'] is False
    
    def test_create_class_nodes(self):
        """Test class node creation."""
        parser_output = {
            'classes': [
                {
                    'name': 'TestClass',
                    'qualified_name': 'module.TestClass',
                    'line_start': 1,
                    'line_end': 50,
                    'base_classes': ['BaseClass', 'Mixin'],
                    'methods': [
                        {'name': 'method1'},
                        {'name': 'method2'}
                    ],
                    'attributes': ['attr1', 'attr2'],
                    'decorators': ['@dataclass'],
                    'docstring': 'Test class',
                    'is_abstract': True
                }
            ]
        }
        
        class_nodes = self.builder._create_class_nodes(parser_output, '/test/file.py')
        
        assert len(class_nodes) == 1
        class_node = class_nodes[0]
        assert class_node.name == 'TestClass'
        assert class_node.base_classes == ['BaseClass', 'Mixin']
        assert class_node.methods == ['method1', 'method2']
        assert class_node.properties['attributes'] == ['attr1', 'attr2']
        assert class_node.properties['decorators'] == ['@dataclass']
        assert class_node.properties['docstring'] == 'Test class'
        assert class_node.properties['is_abstract'] is True
    
    def test_create_call_edges(self):
        """Test call edge creation."""
        parser_output = {
            'functions': [
                {
                    'name': 'caller',
                    'qualified_name': 'module.caller',
                    'calls': [
                        {'name': 'callee', 'line': 5, 'type': 'direct'},
                        {'name': 'print', 'line': 7, 'arguments': 'hello'}
                    ]
                }
            ]
        }
        
        # Create function nodes first
        function_nodes = self.builder._create_function_nodes(parser_output, '/test/file.py')
        
        call_edges = self.builder._create_call_edges(parser_output, function_nodes, '/test/file.py')
        
        assert len(call_edges) >= 1
        # Check that edges have proper source and target
        for edge in call_edges:
            assert edge.source.startswith('function:')
            assert edge.target.startswith('function:')
            assert edge.type == 'calls'
    
    def test_create_inheritance_edges(self):
        """Test inheritance edge creation."""
        # Create class nodes
        class_nodes = [
            ClassNode(
                id='class:/test/file.py:Child',
                name='Child',
                qualified_name='module.Child',
                line_start=1,
                line_end=10,
                base_classes=['Parent', 'Mixin']
            ),
            ClassNode(
                id='class:/test/file.py:Parent',
                name='Parent',
                qualified_name='module.Parent',
                line_start=11,
                line_end=20,
                base_classes=[]
            )
        ]
        
        inheritance_edges = self.builder._create_inheritance_edges(class_nodes, '/test/file.py')
        
        assert len(inheritance_edges) == 2  # Child inherits from Parent and Mixin
        
        # Check edge properties
        for edge in inheritance_edges:
            assert edge.type == 'inherits'
            assert edge.source == 'class:/test/file.py:Child'
            assert edge.target.startswith('class:')
    
    def test_create_import_edges(self):
        """Test import edge creation."""
        parser_output = {
            'imports': [
                {
                    'module': 'os',
                    'type': 'import',
                    'line_number': 1
                },
                {
                    'module': 'sys',
                    'type': 'from',
                    'alias': 'system',
                    'line_number': 2
                }
            ]
        }
        
        file_id = 'file:/test/file.py'
        import_edges = self.builder._create_import_edges(parser_output, file_id)
        
        assert len(import_edges) == 2
        
        for edge in import_edges:
            assert edge.source == file_id
            assert edge.target.startswith('module:')
            assert edge.type == 'imports'
    
    def test_empty_parser_output(self):
        """Test handling empty parser output."""
        parser_output = {
            'file_path': '/test/empty.py',
            'language': 'python',
            'functions': [],
            'classes': [],
            'imports': []
        }
        
        graph = self.builder.from_parser_output(parser_output)
        
        # Should still create file node
        file_nodes = graph.get_nodes_by_type('file')
        assert len(file_nodes) == 1
        
        # But no other nodes
        function_nodes = graph.get_nodes_by_type('function')
        assert len(function_nodes) == 0
        
        class_nodes = graph.get_nodes_by_type('class')
        assert len(class_nodes) == 0
    
    def test_malformed_parser_output(self):
        """Test handling malformed parser output."""
        # Missing required fields
        parser_output = {
            'file_path': '/test/malformed.py',
            'functions': [
                {
                    'name': 'func_without_lines'
                    # Missing line_start, line_end
                }
            ]
        }
        
        # Should not crash, but may create nodes with default values
        graph = self.builder.from_parser_output(parser_output)
        
        file_nodes = graph.get_nodes_by_type('file')
        assert len(file_nodes) == 1
    
    def test_builtin_function_detection(self):
        """Test builtin function detection."""
        assert self.builder._is_builtin('print')
        assert self.builder._is_builtin('len')
        assert self.builder._is_builtin('str')
        assert not self.builder._is_builtin('custom_function')
        assert not self.builder._is_builtin('user_defined')
    
    def test_resolution_cache(self):
        """Test call target resolution caching."""
        func_lookup = {'func1': 'function:/test/file.py:func1'}
        
        # First resolution
        target1 = self.builder._resolve_call_target('func1', func_lookup, '/test/file.py')
        
        # Second resolution should use cache
        target2 = self.builder._resolve_call_target('func1', func_lookup, '/test/file.py')
        
        assert target1 == target2
        
        # Check cache was used
        cache_key = '/test/file.py:func1'
        assert cache_key in self.builder._resolution_cache
        assert self.builder._resolution_cache[cache_key] == target1


if __name__ == "__main__":
    pytest.main([__file__])