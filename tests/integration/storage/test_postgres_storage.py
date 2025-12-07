"""
Integration tests for PostgreSQL storage adapter.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch

from codesage.graph.storage.postgres_impl import PostgreSQLStorageAdapter, PostgresConfig
from codesage.graph.storage.adapter import StorageException, NodeNotFoundError
from codesage.graph.models.node import FunctionNode, ClassNode, FileNode
from codesage.graph.models.edge import CallEdge, InheritanceEdge, ContainsEdge
from codesage.graph.models.graph import Graph


@pytest.fixture
def postgres_config():
    """Create PostgreSQL configuration for testing."""
    return PostgresConfig(
        host='localhost',
        port=5432,
        database='codesage_test',
        username='codesage_test',
        password='codesage_test',
        pool_size=5,
        echo=False  # Set to True for SQL debugging
    )


@pytest.fixture
def postgres_adapter(postgres_config):
    """Create PostgreSQL storage adapter for testing."""
    try:
        adapter = PostgreSQLStorageAdapter(postgres_config)
        # Clear any existing data
        adapter.clear_all()
        yield adapter
        # Cleanup after test
        adapter.clear_all()
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")


@pytest.fixture
def sample_graph():
    """Create a sample graph for testing."""
    graph = Graph()
    
    # Create nodes
    file_node = FileNode(
        id="file:test.py",
        path="/test/test.py",
        language="python",
        loc=50
    )
    
    func1 = FunctionNode(
        id="func:test.py:func1",
        name="func1",
        qualified_name="test.func1",
        line_start=1,
        line_end=10,
        complexity=3,
        params=["arg1", "arg2"]
    )
    
    func2 = FunctionNode(
        id="func:test.py:func2",
        name="func2",
        qualified_name="test.func2",
        line_start=11,
        line_end=20,
        complexity=7,
        params=["arg1"]
    )
    
    class1 = ClassNode(
        id="class:test.py:TestClass",
        name="TestClass",
        qualified_name="test.TestClass",
        line_start=21,
        line_end=40,
        base_classes=["BaseClass"],
        methods=["method1", "method2"]
    )
    
    # Add nodes to graph
    graph.add_node(file_node)
    graph.add_node(func1)
    graph.add_node(func2)
    graph.add_node(class1)
    
    # Create edges
    contains_edge1 = ContainsEdge("file:test.py", "func:test.py:func1", line_number=1)
    contains_edge2 = ContainsEdge("file:test.py", "func:test.py:func2", line_number=11)
    contains_edge3 = ContainsEdge("file:test.py", "class:test.py:TestClass", line_number=21)
    call_edge = CallEdge("func:test.py:func1", "func:test.py:func2", call_site=5)
    
    graph.add_edge(contains_edge1)
    graph.add_edge(contains_edge2)
    graph.add_edge(contains_edge3)
    graph.add_edge(call_edge)
    
    return graph


class TestPostgreSQLStorageAdapter:
    """Test PostgreSQL storage adapter integration."""
    
    def test_save_and_load_graph(self, postgres_adapter, sample_graph):
        """Test saving and loading a complete graph."""
        # Save graph
        postgres_adapter.save_graph(sample_graph)
        
        # Load graph
        loaded_graph = postgres_adapter.load_graph("file:test.py", max_depth=5)
        
        # Verify nodes
        assert len(loaded_graph.nodes) == len(sample_graph.nodes)
        for node_id, original_node in sample_graph.nodes.items():
            assert node_id in loaded_graph.nodes
            loaded_node = loaded_graph.nodes[node_id]
            assert loaded_node.type == original_node.type
            assert loaded_node.properties == original_node.properties
        
        # Verify edges
        assert len(loaded_graph.edges) == len(sample_graph.edges)
        for original_edge in sample_graph.edges:
            assert any(
                e.source == original_edge.source and 
                e.target == original_edge.target and 
                e.type == original_edge.type
                for e in loaded_graph.edges
            )
    
    def test_save_node_individual(self, postgres_adapter):
        """Test saving individual nodes."""
        func_node = FunctionNode(
            id="func:individual",
            name="individual_func",
            qualified_name="test.individual_func",
            line_start=1,
            line_end=10,
            complexity=5
        )
        
        # Save node
        postgres_adapter.save_node(func_node)
        
        # Retrieve node
        retrieved_node = postgres_adapter.get_node("func:individual")
        
        assert retrieved_node.id == func_node.id
        assert retrieved_node.name == func_node.name
        assert retrieved_node.complexity == func_node.complexity
    
    def test_save_edge_individual(self, postgres_adapter):
        """Test saving individual edges."""
        # First save the nodes
        func1 = FunctionNode(
            id="func:source",
            name="source_func",
            qualified_name="test.source_func",
            line_start=1,
            line_end=10
        )
        func2 = FunctionNode(
            id="func:target",
            name="target_func",
            qualified_name="test.target_func",
            line_start=11,
            line_end=20
        )
        
        postgres_adapter.save_node(func1)
        postgres_adapter.save_node(func2)
        
        # Save edge
        call_edge = CallEdge("func:source", "func:target", call_site=5)
        postgres_adapter.save_edge(call_edge)
        
        # Retrieve edges
        edges = postgres_adapter.get_edges("func:source")
        
        assert len(edges) == 1
        assert edges[0].source == "func:source"
        assert edges[0].target == "func:target"
        assert edges[0].type == "calls"
        assert edges[0].call_site == 5
    
    def test_query_nodes_by_type(self, postgres_adapter, sample_graph):
        """Test querying nodes by type."""
        # Save graph
        postgres_adapter.save_graph(sample_graph)
        
        # Query functions
        functions = postgres_adapter.query_nodes("function", {})
        assert len(functions) == 2
        assert all(node.type == "function" for node in functions)
        
        # Query classes
        classes = postgres_adapter.query_nodes("class", {})
        assert len(classes) == 1
        assert classes[0].type == "class"
        
        # Query files
        files = postgres_adapter.query_nodes("file", {})
        assert len(files) == 1
        assert files[0].type == "file"
    
    def test_query_nodes_with_filters(self, postgres_adapter, sample_graph):
        """Test querying nodes with attribute filters."""
        # Save graph
        postgres_adapter.save_graph(sample_graph)
        
        # Query functions with complexity > 5
        high_complexity_funcs = postgres_adapter.query_nodes(
            "function", 
            {"complexity": {"$gt": 5}}
        )
        assert len(high_complexity_funcs) == 1
        assert high_complexity_funcs[0].name == "func2"
        assert high_complexity_funcs[0].complexity == 7
        
        # Query functions with exact complexity
        exact_complexity_funcs = postgres_adapter.query_nodes(
            "function",
            {"complexity": 3}
        )
        assert len(exact_complexity_funcs) == 1
        assert exact_complexity_funcs[0].name == "func1"
    
    def test_query_nodes_with_pagination(self, postgres_adapter):
        """Test querying nodes with pagination."""
        # Create multiple function nodes
        for i in range(10):
            func_node = FunctionNode(
                id=f"func:pagination_test_{i}",
                name=f"func_{i}",
                qualified_name=f"test.func_{i}",
                line_start=i * 10,
                line_end=(i * 10) + 9,
                complexity=i
            )
            postgres_adapter.save_node(func_node)
        
        # Test pagination
        page1 = postgres_adapter.query_nodes("function", {}, limit=5, offset=0)
        page2 = postgres_adapter.query_nodes("function", {}, limit=5, offset=5)
        
        assert len(page1) == 5
        assert len(page2) == 5
        
        # Verify no overlap
        page1_ids = {node.id for node in page1}
        page2_ids = {node.id for node in page2}
        assert len(page1_ids & page2_ids) == 0
    
    def test_delete_node(self, postgres_adapter, sample_graph):
        """Test deleting nodes."""
        # Save graph
        postgres_adapter.save_graph(sample_graph)
        
        # Verify node exists
        assert postgres_adapter.node_exists("func:test.py:func1")
        
        # Delete node
        postgres_adapter.delete_node("func:test.py:func1")
        
        # Verify node is deleted
        assert not postgres_adapter.node_exists("func:test.py:func1")
        
        # Verify node cannot be retrieved
        with pytest.raises(NodeNotFoundError):
            postgres_adapter.get_node("func:test.py:func1")
        
        # Verify connected edges are also deleted
        edges = postgres_adapter.get_edges("func:test.py:func1")
        assert len(edges) == 0
    
    def test_delete_edge(self, postgres_adapter, sample_graph):
        """Test deleting edges."""
        # Save graph
        postgres_adapter.save_graph(sample_graph)
        
        # Verify edge exists
        edges = postgres_adapter.get_edges("func:test.py:func1", edge_type="calls")
        assert len(edges) == 1
        
        # Delete edge
        postgres_adapter.delete_edge("func:test.py:func1", "func:test.py:func2", "calls")
        
        # Verify edge is deleted
        edges = postgres_adapter.get_edges("func:test.py:func1", edge_type="calls")
        assert len(edges) == 0
    
    def test_node_count(self, postgres_adapter, sample_graph):
        """Test getting node counts."""
        # Save graph
        postgres_adapter.save_graph(sample_graph)
        
        # Test total count
        total_count = postgres_adapter.get_node_count()
        assert total_count == 4
        
        # Test count by type
        function_count = postgres_adapter.get_node_count("function")
        assert function_count == 2
        
        class_count = postgres_adapter.get_node_count("class")
        assert class_count == 1
        
        file_count = postgres_adapter.get_node_count("file")
        assert file_count == 1
    
    def test_edge_count(self, postgres_adapter, sample_graph):
        """Test getting edge counts."""
        # Save graph
        postgres_adapter.save_graph(sample_graph)
        
        # Test total count
        total_count = postgres_adapter.get_edge_count()
        assert total_count == 4
        
        # Test count by type
        contains_count = postgres_adapter.get_edge_count("contains")
        assert contains_count == 3
        
        calls_count = postgres_adapter.get_edge_count("calls")
        assert calls_count == 1
    
    def test_transaction_success(self, postgres_adapter):
        """Test successful transaction."""
        func_node = FunctionNode(
            id="func:transaction_test",
            name="transaction_func",
            qualified_name="test.transaction_func",
            line_start=1,
            line_end=10
        )
        
        # Use transaction
        with postgres_adapter.transaction():
            postgres_adapter.save_node(func_node)
        
        # Verify node was saved
        retrieved_node = postgres_adapter.get_node("func:transaction_test")
        assert retrieved_node.id == func_node.id
    
    def test_transaction_rollback(self, postgres_adapter):
        """Test transaction rollback on error."""
        func_node = FunctionNode(
            id="func:rollback_test",
            name="rollback_func",
            qualified_name="test.rollback_func",
            line_start=1,
            line_end=10
        )
        
        # Use transaction that fails
        with pytest.raises(StorageException):
            with postgres_adapter.transaction():
                postgres_adapter.save_node(func_node)
                # Force an error
                raise Exception("Simulated error")
        
        # Verify node was not saved (transaction rolled back)
        assert not postgres_adapter.node_exists("func:rollback_test")
    
    def test_recursive_cte_load(self, postgres_adapter):
        """Test recursive CTE graph loading."""
        # Create a chain of function calls: func1 -> func2 -> func3
        func1 = FunctionNode(
            id="func:chain_1",
            name="func1",
            qualified_name="test.func1",
            line_start=1,
            line_end=10
        )
        func2 = FunctionNode(
            id="func:chain_2",
            name="func2",
            qualified_name="test.func2",
            line_start=11,
            line_end=20
        )
        func3 = FunctionNode(
            id="func:chain_3",
            name="func3",
            qualified_name="test.func3",
            line_start=21,
            line_end=30
        )
        
        # Save nodes
        postgres_adapter.save_node(func1)
        postgres_adapter.save_node(func2)
        postgres_adapter.save_node(func3)
        
        # Save edges
        edge1 = CallEdge("func:chain_1", "func:chain_2")
        edge2 = CallEdge("func:chain_2", "func:chain_3")
        postgres_adapter.save_edge(edge1)
        postgres_adapter.save_edge(edge2)
        
        # Load graph with depth limit
        loaded_graph = postgres_adapter.load_graph("func:chain_1", max_depth=2)
        
        # Should load all 3 nodes and 2 edges
        assert len(loaded_graph.nodes) == 3
        assert len(loaded_graph.edges) == 2
        
        # Test depth limiting
        limited_graph = postgres_adapter.load_graph("func:chain_1", max_depth=1)
        assert len(limited_graph.nodes) == 2  # func1 and func2
        assert len(limited_graph.edges) == 1  # func1 -> func2
    
    def test_load_nonexistent_graph(self, postgres_adapter):
        """Test loading non-existent graph."""
        with pytest.raises(NodeNotFoundError):
            postgres_adapter.load_graph("nonexistent:node")
    
    def test_get_nonexistent_node(self, postgres_adapter):
        """Test getting non-existent node."""
        with pytest.raises(NodeNotFoundError):
            postgres_adapter.get_node("nonexistent:node")
    
    def test_clear_all(self, postgres_adapter, sample_graph):
        """Test clearing all data."""
        # Save graph
        postgres_adapter.save_graph(sample_graph)
        
        # Verify data exists
        assert postgres_adapter.get_node_count() > 0
        
        # Clear all
        postgres_adapter.clear_all()
        
        # Verify data is cleared
        assert postgres_adapter.get_node_count() == 0
        assert postgres_adapter.get_edge_count() == 0
    
    def test_get_statistics(self, postgres_adapter, sample_graph):
        """Test getting storage statistics."""
        # Save graph
        postgres_adapter.save_graph(sample_graph)
        
        # Get statistics
        stats = postgres_adapter.get_statistics()
        
        assert 'total_nodes' in stats
        assert 'total_edges' in stats
        assert stats['total_nodes'] == 4
        assert stats['total_edges'] == 4
    
    def test_concurrent_access(self, postgres_adapter):
        """Test concurrent access to PostgreSQL storage."""
        def save_nodes(start_id, count):
            for i in range(count):
                node = FunctionNode(
                    id=f"func:concurrent_{start_id}_{i}",
                    name=f"func_{start_id}_{i}",
                    qualified_name=f"test.func_{start_id}_{i}",
                    line_start=1,
                    line_end=10
                )
                postgres_adapter.save_node(node)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=save_nodes, args=(i, 10))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all nodes were saved
        total_nodes = postgres_adapter.get_node_count("function")
        assert total_nodes == 50  # 5 threads * 10 nodes each
    
    def test_batch_operations(self, postgres_adapter):
        """Test batch save operations."""
        # Create many nodes
        nodes = []
        for i in range(100):
            func_node = FunctionNode(
                id=f"func:batch_test_{i}",
                name=f"func_{i}",
                qualified_name=f"test.func_{i}",
                line_start=i * 10,
                line_end=(i * 10) + 9,
                complexity=i % 10
            )
            nodes.append(func_node)
        
        # Batch save
        postgres_adapter.bulk_save_nodes(nodes, batch_size=25)
        
        # Verify all nodes were saved
        total_count = postgres_adapter.get_node_count("function")
        assert total_count == 100
    
    def test_upsert_behavior(self, postgres_adapter):
        """Test upsert (insert or update) behavior."""
        # Create initial node
        func_node = FunctionNode(
            id="func:upsert_test",
            name="original_func",
            qualified_name="test.original_func",
            line_start=1,
            line_end=10,
            complexity=5
        )
        
        # Save initial node
        postgres_adapter.save_node(func_node)
        
        # Verify initial save
        retrieved = postgres_adapter.get_node("func:upsert_test")
        assert retrieved.name == "original_func"
        assert retrieved.complexity == 5
        
        # Update node with same ID
        updated_func_node = FunctionNode(
            id="func:upsert_test",
            name="updated_func",
            qualified_name="test.updated_func",
            line_start=1,
            line_end=15,
            complexity=8
        )
        
        # Save updated node (should upsert)
        postgres_adapter.save_node(updated_func_node)
        
        # Verify update
        retrieved = postgres_adapter.get_node("func:upsert_test")
        assert retrieved.name == "updated_func"
        assert retrieved.complexity == 8
        
        # Verify only one node exists
        total_count = postgres_adapter.get_node_count("function")
        assert total_count == 1
    
    def test_jsonb_queries(self, postgres_adapter):
        """Test JSONB property queries."""
        # Create nodes with different properties
        func1 = FunctionNode(
            id="func:jsonb_test_1",
            name="func1",
            qualified_name="test.func1",
            line_start=1,
            line_end=10,
            complexity=5,
            params=["arg1", "arg2"]
        )
        
        func2 = FunctionNode(
            id="func:jsonb_test_2",
            name="func2",
            qualified_name="test.func2",
            line_start=11,
            line_end=20,
            complexity=15,
            params=["arg1"]
        )
        
        postgres_adapter.save_node(func1)
        postgres_adapter.save_node(func2)
        
        # Query by complexity range
        high_complexity = postgres_adapter.query_nodes(
            "function",
            {"complexity": {"$gt": 10}}
        )
        assert len(high_complexity) == 1
        assert high_complexity[0].name == "func2"
        
        # Query by exact match
        exact_match = postgres_adapter.query_nodes(
            "function",
            {"name": "func1"}
        )
        assert len(exact_match) == 1
        assert exact_match[0].name == "func1"
    
    def test_large_graph_performance(self, postgres_adapter):
        """Test performance with larger graphs."""
        # Create a larger graph
        graph = Graph()
        
        # Add 1000 function nodes
        for i in range(1000):
            func_node = FunctionNode(
                id=f"func:large_test_{i}",
                name=f"func_{i}",
                qualified_name=f"test.func_{i}",
                line_start=i * 10,
                line_end=(i * 10) + 9,
                complexity=i % 10
            )
            graph.add_node(func_node)
        
        # Add edges between functions (every 10th function calls the next)
        for i in range(0, 990, 10):
            call_edge = CallEdge(f"func:large_test_{i}", f"func:large_test_{i+10}")
            graph.add_edge(call_edge)
        
        # Measure save time
        start_time = time.time()
        postgres_adapter.save_graph(graph, batch_size=100)
        save_time = time.time() - start_time
        
        # Should save reasonably quickly (< 5 seconds for 1000 nodes)
        assert save_time < 5.0
        
        # Measure load time
        start_time = time.time()
        loaded_graph = postgres_adapter.load_graph("func:large_test_0", max_depth=3)
        load_time = time.time() - start_time
        
        # Should load reasonably quickly
        assert load_time < 3.0
        
        # Verify some data was loaded
        assert len(loaded_graph.nodes) > 0
        assert len(loaded_graph.edges) >= 0


if __name__ == "__main__":
    pytest.main([__file__])