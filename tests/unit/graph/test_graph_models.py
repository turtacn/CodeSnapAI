"""
Unit tests for graph models (Node, Edge, Graph, GraphDelta).
"""

import pytest
import json
import msgpack
from unittest.mock import Mock

from codesage.graph.models.node import (
    Node, FunctionNode, ClassNode, FileNode, ModuleNode, VariableNode, create_node_id
)
from codesage.graph.models.edge import (
    Edge, CallEdge, InheritanceEdge, ImportEdge, ContainsEdge, ReferencesEdge, DefinesEdge
)
from codesage.graph.models.graph import Graph, GraphDelta


class TestNodeModels:
    """Test node model classes."""
    
    def test_function_node_creation(self):
        """Test FunctionNode creation and properties."""
        func_node = FunctionNode(
            id="test:func1",
            name="func1",
            qualified_name="module.func1",
            line_start=10,
            line_end=20,
            complexity=5,
            params=["arg1", "arg2"],
            return_type="str"
        )
        
        assert func_node.id == "test:func1"
        assert func_node.type == "function"
        assert func_node.name == "func1"
        assert func_node.qualified_name == "module.func1"
        assert func_node.line_start == 10
        assert func_node.line_end == 20
        assert func_node.complexity == 5
        assert func_node.params == ["arg1", "arg2"]
        assert func_node.return_type == "str"
        assert func_node.get_qualified_name() == "module.func1"
    
    def test_class_node_creation(self):
        """Test ClassNode creation and properties."""
        class_node = ClassNode(
            id="test:Class1",
            name="Class1",
            qualified_name="module.Class1",
            line_start=1,
            line_end=50,
            base_classes=["BaseClass"],
            methods=["method1", "method2"]
        )
        
        assert class_node.id == "test:Class1"
        assert class_node.type == "class"
        assert class_node.name == "Class1"
        assert class_node.base_classes == ["BaseClass"]
        assert class_node.methods == ["method1", "method2"]
    
    def test_file_node_creation(self):
        """Test FileNode creation and properties."""
        file_node = FileNode(
            id="file:test.py",
            path="/path/to/test.py",
            language="python",
            loc=100
        )
        
        assert file_node.id == "file:test.py"
        assert file_node.type == "file"
        assert file_node.path == "/path/to/test.py"
        assert file_node.language == "python"
        assert file_node.loc == 100
    
    def test_module_node_creation(self):
        """Test ModuleNode creation and properties."""
        module_node = ModuleNode(
            id="module:test_module",
            name="test_module",
            qualified_name="package.test_module"
        )
        
        assert module_node.id == "module:test_module"
        assert module_node.type == "module"
        assert module_node.name == "test_module"
        assert module_node.qualified_name == "package.test_module"
    
    def test_variable_node_creation(self):
        """Test VariableNode creation and properties."""
        var_node = VariableNode(
            id="var:test_var",
            name="test_var",
            qualified_name="module.test_var",
            type_hint="int",
            value="42"
        )
        
        assert var_node.id == "var:test_var"
        assert var_node.type == "variable"
        assert var_node.name == "test_var"
        assert var_node.type_hint == "int"
        assert var_node.value == "42"
    
    def test_node_serialization(self):
        """Test node to_dict and from_dict methods."""
        func_node = FunctionNode(
            id="test:func1",
            name="func1",
            qualified_name="module.func1",
            line_start=10,
            line_end=20,
            complexity=5
        )
        
        # Test to_dict
        node_dict = func_node.to_dict()
        assert node_dict['id'] == "test:func1"
        assert node_dict['type'] == "function"
        assert node_dict['properties']['name'] == "func1"
        assert node_dict['properties']['complexity'] == 5
        
        # Test from_dict
        restored_node = Node.from_dict(node_dict)
        assert isinstance(restored_node, FunctionNode)
        assert restored_node.id == func_node.id
        assert restored_node.name == func_node.name
        assert restored_node.complexity == func_node.complexity
    
    def test_create_node_id(self):
        """Test node ID creation utility."""
        # Normal case
        node_id = create_node_id("function", "module.func1", "/path/to/file.py")
        assert node_id == "function:/path/to/file.py:module.func1"
        
        # Without file path
        node_id = create_node_id("module", "package.module")
        assert node_id == "module:package.module"
        
        # Very long name (should be hashed)
        long_name = "very_long_qualified_name_" * 20
        node_id = create_node_id("function", long_name)
        assert len(node_id) < 250  # Should be truncated and hashed
        assert node_id.startswith("function:")


class TestEdgeModels:
    """Test edge model classes."""
    
    def test_call_edge_creation(self):
        """Test CallEdge creation and properties."""
        call_edge = CallEdge(
            source="func1",
            target="func2",
            call_site=15,
            call_type="direct"
        )
        
        assert call_edge.source == "func1"
        assert call_edge.target == "func2"
        assert call_edge.type == "calls"
        assert call_edge.call_site == 15
        assert call_edge.call_type == "direct"
    
    def test_inheritance_edge_creation(self):
        """Test InheritanceEdge creation and properties."""
        inherit_edge = InheritanceEdge(
            source="ChildClass",
            target="ParentClass",
            inheritance_type="single"
        )
        
        assert inherit_edge.source == "ChildClass"
        assert inherit_edge.target == "ParentClass"
        assert inherit_edge.type == "inherits"
        assert inherit_edge.inheritance_type == "single"
    
    def test_import_edge_creation(self):
        """Test ImportEdge creation and properties."""
        import_edge = ImportEdge(
            source="file1",
            target="module1",
            import_type="from",
            alias="mod",
            line_number=5
        )
        
        assert import_edge.source == "file1"
        assert import_edge.target == "module1"
        assert import_edge.type == "imports"
        assert import_edge.import_type == "from"
        assert import_edge.alias == "mod"
        assert import_edge.line_number == 5
    
    def test_contains_edge_creation(self):
        """Test ContainsEdge creation and properties."""
        contains_edge = ContainsEdge(
            source="file1",
            target="func1",
            line_number=10
        )
        
        assert contains_edge.source == "file1"
        assert contains_edge.target == "func1"
        assert contains_edge.type == "contains"
        assert contains_edge.line_number == 10
    
    def test_edge_serialization(self):
        """Test edge to_dict and from_dict methods."""
        call_edge = CallEdge(
            source="func1",
            target="func2",
            call_site=15
        )
        
        # Test to_dict
        edge_dict = call_edge.to_dict()
        assert edge_dict['source'] == "func1"
        assert edge_dict['target'] == "func2"
        assert edge_dict['type'] == "calls"
        assert edge_dict['properties']['call_site'] == 15
        
        # Test from_dict
        restored_edge = Edge.from_dict(edge_dict)
        assert isinstance(restored_edge, CallEdge)
        assert restored_edge.source == call_edge.source
        assert restored_edge.target == call_edge.target
        assert restored_edge.call_site == call_edge.call_site
    
    def test_edge_equality(self):
        """Test edge equality comparison."""
        edge1 = CallEdge("func1", "func2", call_site=10)
        edge2 = CallEdge("func1", "func2", call_site=20)  # Different properties
        edge3 = CallEdge("func1", "func3", call_site=10)  # Different target
        
        assert edge1 == edge2  # Same source, target, type
        assert edge1 != edge3  # Different target
        assert hash(edge1) == hash(edge2)
        assert hash(edge1) != hash(edge3)


class TestGraph:
    """Test Graph class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.graph = Graph()
        
        # Create test nodes
        self.func1 = FunctionNode(
            id="func:func1",
            name="func1",
            qualified_name="module.func1",
            line_start=1,
            line_end=10
        )
        self.func2 = FunctionNode(
            id="func:func2",
            name="func2",
            qualified_name="module.func2",
            line_start=11,
            line_end=20
        )
        self.file1 = FileNode(
            id="file:test.py",
            path="test.py",
            language="python",
            loc=50
        )
        
        # Create test edges
        self.call_edge = CallEdge("func:func1", "func:func2", call_site=5)
        self.contains_edge1 = ContainsEdge("file:test.py", "func:func1")
        self.contains_edge2 = ContainsEdge("file:test.py", "func:func2")
    
    def test_add_node(self):
        """Test adding nodes to graph."""
        self.graph.add_node(self.func1)
        assert self.func1.id in self.graph.nodes
        assert self.graph.has_node(self.func1.id)
        assert len(self.graph) == 1
    
    def test_add_edge(self):
        """Test adding edges to graph."""
        # Add nodes first
        self.graph.add_node(self.func1)
        self.graph.add_node(self.func2)
        
        # Add edge
        self.graph.add_edge(self.call_edge)
        assert self.call_edge in self.graph.edges
        assert self.graph.has_edge("func:func1", "func:func2", "calls")
    
    def test_add_edge_without_nodes_fails(self):
        """Test that adding edge without nodes raises error."""
        with pytest.raises(ValueError, match="Cannot add edge"):
            self.graph.add_edge(self.call_edge)
    
    def test_remove_node(self):
        """Test removing nodes from graph."""
        # Add nodes and edges
        self.graph.add_node(self.func1)
        self.graph.add_node(self.func2)
        self.graph.add_edge(self.call_edge)
        
        # Remove node
        self.graph.remove_node(self.func1.id)
        
        assert self.func1.id not in self.graph.nodes
        assert self.call_edge not in self.graph.edges  # Edge should be removed too
    
    def test_get_neighbors(self):
        """Test getting node neighbors."""
        # Build graph
        self.graph.add_node(self.file1)
        self.graph.add_node(self.func1)
        self.graph.add_node(self.func2)
        self.graph.add_edge(self.contains_edge1)
        self.graph.add_edge(self.contains_edge2)
        self.graph.add_edge(self.call_edge)
        
        # Test outgoing neighbors
        out_neighbors = self.graph.get_neighbors("file:test.py", "out")
        assert "func:func1" in out_neighbors
        assert "func:func2" in out_neighbors
        
        # Test incoming neighbors
        in_neighbors = self.graph.get_neighbors("func:func1", "in")
        assert "file:test.py" in in_neighbors
        
        # Test both directions
        all_neighbors = self.graph.get_neighbors("func:func1", "both")
        assert "file:test.py" in all_neighbors
        assert "func:func2" in all_neighbors
    
    def test_get_nodes_by_type(self):
        """Test filtering nodes by type."""
        self.graph.add_node(self.file1)
        self.graph.add_node(self.func1)
        self.graph.add_node(self.func2)
        
        functions = self.graph.get_nodes_by_type("function")
        assert len(functions) == 2
        assert self.func1 in functions
        assert self.func2 in functions
        
        files = self.graph.get_nodes_by_type("file")
        assert len(files) == 1
        assert self.file1 in files
    
    def test_get_edges_by_type(self):
        """Test filtering edges by type."""
        self.graph.add_node(self.file1)
        self.graph.add_node(self.func1)
        self.graph.add_node(self.func2)
        self.graph.add_edge(self.contains_edge1)
        self.graph.add_edge(self.call_edge)
        
        call_edges = self.graph.get_edges_by_type("calls")
        assert len(call_edges) == 1
        assert self.call_edge in call_edges
        
        contains_edges = self.graph.get_edges_by_type("contains")
        assert len(contains_edges) == 1
        assert self.contains_edge1 in contains_edges
    
    def test_traverse_bfs(self):
        """Test breadth-first traversal."""
        # Build linear graph: file -> func1 -> func2
        self.graph.add_node(self.file1)
        self.graph.add_node(self.func1)
        self.graph.add_node(self.func2)
        self.graph.add_edge(self.contains_edge1)
        self.graph.add_edge(self.call_edge)
        
        # Traverse from file
        traversal = list(self.graph.traverse_bfs("file:test.py"))
        
        assert len(traversal) == 3
        assert traversal[0] == ("file:test.py", 0)
        assert traversal[1] == ("func:func1", 1)
        assert traversal[2] == ("func:func2", 2)
    
    def test_traverse_dfs(self):
        """Test depth-first traversal."""
        # Build linear graph: file -> func1 -> func2
        self.graph.add_node(self.file1)
        self.graph.add_node(self.func1)
        self.graph.add_node(self.func2)
        self.graph.add_edge(self.contains_edge1)
        self.graph.add_edge(self.call_edge)
        
        # Traverse from file
        traversal = list(self.graph.traverse_dfs("file:test.py"))
        
        assert len(traversal) == 3
        assert traversal[0] == ("file:test.py", 0)
        # DFS should go deep first
        assert ("func:func1", 1) in traversal
        assert ("func:func2", 2) in traversal
    
    def test_graph_serialization_json(self):
        """Test graph JSON serialization."""
        self.graph.add_node(self.func1)
        self.graph.add_node(self.func2)
        self.graph.add_edge(self.call_edge)
        
        # Test to_json
        json_str = self.graph.to_json()
        assert isinstance(json_str, str)
        
        # Test from_json
        restored_graph = Graph.from_json(json_str)
        assert len(restored_graph.nodes) == 2
        assert len(restored_graph.edges) == 1
        assert restored_graph.has_node("func:func1")
        assert restored_graph.has_node("func:func2")
        assert restored_graph.has_edge("func:func1", "func:func2", "calls")
    
    def test_graph_serialization_msgpack(self):
        """Test graph MessagePack serialization."""
        self.graph.add_node(self.func1)
        self.graph.add_node(self.func2)
        self.graph.add_edge(self.call_edge)
        
        # Test to_msgpack
        msgpack_data = self.graph.to_msgpack()
        assert isinstance(msgpack_data, bytes)
        
        # Test from_msgpack
        restored_graph = Graph.from_msgpack(msgpack_data)
        assert len(restored_graph.nodes) == 2
        assert len(restored_graph.edges) == 1
        assert restored_graph.has_node("func:func1")
        assert restored_graph.has_node("func:func2")


class TestGraphDelta:
    """Test GraphDelta class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.delta = GraphDelta()
        self.func1 = FunctionNode(
            id="func:func1",
            name="func1",
            qualified_name="module.func1",
            line_start=1,
            line_end=10
        )
        self.func2 = FunctionNode(
            id="func:func2",
            name="func2",
            qualified_name="module.func2",
            line_start=11,
            line_end=20
        )
        self.call_edge = CallEdge("func:func1", "func:func2")
    
    def test_add_operations(self):
        """Test adding operations to delta."""
        self.delta.add_node(self.func1)
        self.delta.add_edge(self.call_edge)
        
        assert len(self.delta.added_nodes) == 1
        assert len(self.delta.added_edges) == 1
        assert self.func1 in self.delta.added_nodes
        assert self.call_edge in self.delta.added_edges
    
    def test_delete_operations(self):
        """Test delete operations in delta."""
        self.delta.delete_node("func:func1")
        self.delta.delete_edge("func:func1", "func:func2", "calls")
        
        assert len(self.delta.deleted_nodes) == 1
        assert len(self.delta.deleted_edges) == 1
        assert "func:func1" in self.delta.deleted_nodes
        assert ("func:func1", "func:func2", "calls") in self.delta.deleted_edges
    
    def test_update_operations(self):
        """Test update operations in delta."""
        self.delta.update_node(self.func1)
        
        assert len(self.delta.updated_nodes) == 1
        assert self.func1 in self.delta.updated_nodes
    
    def test_has_changes(self):
        """Test has_changes method."""
        assert not self.delta.has_changes()
        
        self.delta.add_node(self.func1)
        assert self.delta.has_changes()
    
    def test_apply_to_graph(self):
        """Test applying delta to graph."""
        # Create initial graph
        graph = Graph()
        graph.add_node(self.func1)
        
        # Create delta that adds func2 and edge
        self.delta.add_node(self.func2)
        self.delta.add_edge(self.call_edge)
        
        # Apply delta
        self.delta.apply_to(graph)
        
        assert graph.has_node("func:func2")
        assert graph.has_edge("func:func1", "func:func2", "calls")
    
    def test_apply_delete_to_graph(self):
        """Test applying delete operations to graph."""
        # Create initial graph
        graph = Graph()
        graph.add_node(self.func1)
        graph.add_node(self.func2)
        graph.add_edge(self.call_edge)
        
        # Create delta that deletes func1
        self.delta.delete_node("func:func1")
        
        # Apply delta
        self.delta.apply_to(graph)
        
        assert not graph.has_node("func:func1")
        assert not graph.has_edge("func:func1", "func:func2", "calls")  # Edge should be removed too


if __name__ == "__main__":
    pytest.main([__file__])