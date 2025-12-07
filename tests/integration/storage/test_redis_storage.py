"""
Integration tests for Redis storage adapter.
"""

import pytest
import time
from unittest.mock import Mock, patch

from codesage.graph.storage.redis_impl import RedisStorageAdapter, RedisConfig
from codesage.graph.storage.adapter import StorageException, NodeNotFoundError
from codesage.graph.models.node import FunctionNode, ClassNode, FileNode
from codesage.graph.models.edge import CallEdge, InheritanceEdge, ContainsEdge
from codesage.graph.models.graph import Graph


@pytest.fixture
def redis_config():
    """Create Redis configuration for testing."""
    return RedisConfig(
        host='localhost',
        port=6379,
        db=15,  # Use separate DB for testing
        default_ttl=60  # Short TTL for testing
    )


@pytest.fixture
def redis_adapter(redis_config):
    """Create Redis storage adapter for testing."""
    try:
        adapter = RedisStorageAdapter(redis_config)
        # Clear any existing data
        adapter.clear_all()
        yield adapter
        # Cleanup after test
        adapter.clear_all()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")


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


class TestRedisStorageAdapter:
    """Test Redis storage adapter integration."""
    
    def test_save_and_load_graph(self, redis_adapter, sample_graph):
        """Test saving and loading a complete graph."""
        # Save graph
        redis_adapter.save_graph(sample_graph, ttl=300)
        
        # Load graph
        loaded_graph = redis_adapter.load_graph("file:test.py", max_depth=5)
        
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
    
    def test_save_node_individual(self, redis_adapter):
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
        redis_adapter.save_node(func_node)
        
        # Retrieve node
        retrieved_node = redis_adapter.get_node("func:individual")
        
        assert retrieved_node.id == func_node.id
        assert retrieved_node.name == func_node.name
        assert retrieved_node.complexity == func_node.complexity
    
    def test_save_edge_individual(self, redis_adapter):
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
        
        redis_adapter.save_node(func1)
        redis_adapter.save_node(func2)
        
        # Save edge
        call_edge = CallEdge("func:source", "func:target", call_site=5)
        redis_adapter.save_edge(call_edge)
        
        # Retrieve edges
        edges = redis_adapter.get_edges("func:source")
        
        assert len(edges) == 1
        assert edges[0].source == "func:source"
        assert edges[0].target == "func:target"
        assert edges[0].type == "calls"
        assert edges[0].call_site == 5
    
    def test_query_nodes_by_type(self, redis_adapter, sample_graph):
        """Test querying nodes by type."""
        # Save graph
        redis_adapter.save_graph(sample_graph)
        
        # Query functions
        functions = redis_adapter.query_nodes("function", {})
        assert len(functions) == 2
        assert all(node.type == "function" for node in functions)
        
        # Query classes
        classes = redis_adapter.query_nodes("class", {})
        assert len(classes) == 1
        assert classes[0].type == "class"
        
        # Query files
        files = redis_adapter.query_nodes("file", {})
        assert len(files) == 1
        assert files[0].type == "file"
    
    def test_query_nodes_with_filters(self, redis_adapter, sample_graph):
        """Test querying nodes with attribute filters."""
        # Save graph
        redis_adapter.save_graph(sample_graph)
        
        # Query functions with complexity > 5
        high_complexity_funcs = redis_adapter.query_nodes(
            "function", 
            {"complexity": {"$gt": 5}}
        )
        assert len(high_complexity_funcs) == 1
        assert high_complexity_funcs[0].name == "func2"
        assert high_complexity_funcs[0].complexity == 7
        
        # Query functions with exact complexity
        exact_complexity_funcs = redis_adapter.query_nodes(
            "function",
            {"complexity": 3}
        )
        assert len(exact_complexity_funcs) == 1
        assert exact_complexity_funcs[0].name == "func1"
    
    def test_delete_node(self, redis_adapter, sample_graph):
        """Test deleting nodes."""
        # Save graph
        redis_adapter.save_graph(sample_graph)
        
        # Verify node exists
        assert redis_adapter.node_exists("func:test.py:func1")
        
        # Delete node
        redis_adapter.delete_node("func:test.py:func1")
        
        # Verify node is deleted
        assert not redis_adapter.node_exists("func:test.py:func1")
        
        # Verify node cannot be retrieved
        with pytest.raises(NodeNotFoundError):
            redis_adapter.get_node("func:test.py:func1")
    
    def test_delete_edge(self, redis_adapter, sample_graph):
        """Test deleting edges."""
        # Save graph
        redis_adapter.save_graph(sample_graph)
        
        # Verify edge exists
        edges = redis_adapter.get_edges("func:test.py:func1", edge_type="calls")
        assert len(edges) == 1
        
        # Delete edge
        redis_adapter.delete_edge("func:test.py:func1", "func:test.py:func2", "calls")
        
        # Verify edge is deleted
        edges = redis_adapter.get_edges("func:test.py:func1", edge_type="calls")
        assert len(edges) == 0
    
    def test_node_count(self, redis_adapter, sample_graph):
        """Test getting node counts."""
        # Save graph
        redis_adapter.save_graph(sample_graph)
        
        # Test total count
        total_count = redis_adapter.get_node_count()
        assert total_count == 4
        
        # Test count by type
        function_count = redis_adapter.get_node_count("function")
        assert function_count == 2
        
        class_count = redis_adapter.get_node_count("class")
        assert class_count == 1
        
        file_count = redis_adapter.get_node_count("file")
        assert file_count == 1
    
    def test_edge_count(self, redis_adapter, sample_graph):
        """Test getting edge counts."""
        # Save graph
        redis_adapter.save_graph(sample_graph)
        
        # Test total count
        total_count = redis_adapter.get_edge_count()
        assert total_count == 4
        
        # Test count by type
        contains_count = redis_adapter.get_edge_count("contains")
        assert contains_count == 3
        
        calls_count = redis_adapter.get_edge_count("calls")
        assert calls_count == 1
    
    def test_transaction_success(self, redis_adapter):
        """Test successful transaction."""
        func_node = FunctionNode(
            id="func:transaction_test",
            name="transaction_func",
            qualified_name="test.transaction_func",
            line_start=1,
            line_end=10
        )
        
        # Use transaction
        with redis_adapter.transaction():
            redis_adapter.save_node(func_node)
        
        # Verify node was saved
        retrieved_node = redis_adapter.get_node("func:transaction_test")
        assert retrieved_node.id == func_node.id
    
    def test_transaction_rollback(self, redis_adapter):
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
            with redis_adapter.transaction():
                redis_adapter.save_node(func_node)
                # Force an error
                raise Exception("Simulated error")
        
        # Verify node was not saved (transaction rolled back)
        assert not redis_adapter.node_exists("func:rollback_test")
    
    def test_ttl_expiration(self, redis_adapter):
        """Test TTL expiration of stored data."""
        func_node = FunctionNode(
            id="func:ttl_test",
            name="ttl_func",
            qualified_name="test.ttl_func",
            line_start=1,
            line_end=10
        )
        
        # Save with very short TTL
        graph = Graph()
        graph.add_node(func_node)
        redis_adapter.save_graph(graph, ttl=1)  # 1 second TTL
        
        # Verify node exists immediately
        assert redis_adapter.node_exists("func:ttl_test")
        
        # Wait for expiration
        time.sleep(2)
        
        # Verify node has expired
        assert not redis_adapter.node_exists("func:ttl_test")
    
    def test_load_nonexistent_graph(self, redis_adapter):
        """Test loading non-existent graph."""
        with pytest.raises(NodeNotFoundError):
            redis_adapter.load_graph("nonexistent:node")
    
    def test_get_nonexistent_node(self, redis_adapter):
        """Test getting non-existent node."""
        with pytest.raises(NodeNotFoundError):
            redis_adapter.get_node("nonexistent:node")
    
    def test_clear_all(self, redis_adapter, sample_graph):
        """Test clearing all data."""
        # Save graph
        redis_adapter.save_graph(sample_graph)
        
        # Verify data exists
        assert redis_adapter.get_node_count() > 0
        
        # Clear all
        redis_adapter.clear_all()
        
        # Verify data is cleared
        assert redis_adapter.get_node_count() == 0
        assert redis_adapter.get_edge_count() == 0
    
    def test_get_statistics(self, redis_adapter, sample_graph):
        """Test getting storage statistics."""
        # Save graph
        redis_adapter.save_graph(sample_graph)
        
        # Get statistics
        stats = redis_adapter.get_statistics()
        
        assert 'total_nodes' in stats
        assert 'total_edges' in stats
        assert stats['total_nodes'] == 4
        assert stats['total_edges'] == 4
    
    def test_concurrent_access(self, redis_adapter):
        """Test concurrent access to Redis storage."""
        import threading
        import time
        
        def save_nodes(start_id, count):
            for i in range(count):
                node = FunctionNode(
                    id=f"func:concurrent_{start_id}_{i}",
                    name=f"func_{start_id}_{i}",
                    qualified_name=f"test.func_{start_id}_{i}",
                    line_start=1,
                    line_end=10
                )
                redis_adapter.save_node(node)
        
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
        total_nodes = redis_adapter.get_node_count("function")
        assert total_nodes == 50  # 5 threads * 10 nodes each
    
    def test_large_graph_performance(self, redis_adapter):
        """Test performance with larger graphs."""
        # Create a larger graph
        graph = Graph()
        
        # Add 100 function nodes
        for i in range(100):
            func_node = FunctionNode(
                id=f"func:large_test_{i}",
                name=f"func_{i}",
                qualified_name=f"test.func_{i}",
                line_start=i * 10,
                line_end=(i * 10) + 9,
                complexity=i % 10
            )
            graph.add_node(func_node)
        
        # Add edges between functions
        for i in range(99):
            call_edge = CallEdge(f"func:large_test_{i}", f"func:large_test_{i+1}")
            graph.add_edge(call_edge)
        
        # Measure save time
        start_time = time.time()
        redis_adapter.save_graph(graph)
        save_time = time.time() - start_time
        
        # Should save reasonably quickly (< 1 second for 100 nodes)
        assert save_time < 1.0
        
        # Measure load time
        start_time = time.time()
        loaded_graph = redis_adapter.load_graph("func:large_test_0", max_depth=10)
        load_time = time.time() - start_time
        
        # Should load reasonably quickly
        assert load_time < 2.0
        
        # Verify data integrity
        assert len(loaded_graph.nodes) == 100
        assert len(loaded_graph.edges) == 99


if __name__ == "__main__":
    pytest.main([__file__])