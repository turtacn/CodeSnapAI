"""
Performance tests for graph query operations.
"""

import pytest
import time
import statistics
from unittest.mock import Mock

from codesage.graph.models.node import FunctionNode, ClassNode, FileNode
from codesage.graph.models.edge import CallEdge, InheritanceEdge, ContainsEdge
from codesage.graph.models.graph import Graph
from codesage.graph.query.dsl import parse_query
from codesage.graph.query.processor import QueryProcessor
from codesage.graph.storage.adapter import StorageAdapter


@pytest.fixture
def large_graph():
    """Create a large graph for performance testing."""
    graph = Graph()
    
    # Create file nodes
    for file_idx in range(10):
        file_node = FileNode(
            id=f"file:file_{file_idx}.py",
            path=f"/test/file_{file_idx}.py",
            language="python",
            loc=100 + file_idx * 10
        )
        graph.add_node(file_node)
        
        # Create function nodes for each file
        for func_idx in range(100):
            func_node = FunctionNode(
                id=f"func:file_{file_idx}:func_{func_idx}",
                name=f"func_{func_idx}",
                qualified_name=f"file_{file_idx}.func_{func_idx}",
                line_start=func_idx * 10,
                line_end=(func_idx * 10) + 9,
                complexity=(func_idx % 20) + 1  # Complexity 1-20
            )
            graph.add_node(func_node)
            
            # Add contains edge
            contains_edge = ContainsEdge(
                file_node.id,
                func_node.id,
                line_number=func_idx * 10
            )
            graph.add_edge(contains_edge)
        
        # Create class nodes for each file
        for class_idx in range(10):
            class_node = ClassNode(
                id=f"class:file_{file_idx}:class_{class_idx}",
                name=f"Class_{class_idx}",
                qualified_name=f"file_{file_idx}.Class_{class_idx}",
                line_start=1000 + class_idx * 50,
                line_end=1000 + (class_idx * 50) + 49,
                methods=[f"method_{i}" for i in range(5)]
            )
            graph.add_node(class_node)
            
            # Add contains edge
            contains_edge = ContainsEdge(
                file_node.id,
                class_node.id,
                line_number=1000 + class_idx * 50
            )
            graph.add_edge(contains_edge)
    
    # Add call edges between functions
    for file_idx in range(10):
        for func_idx in range(99):  # Each function calls the next one
            source_id = f"func:file_{file_idx}:func_{func_idx}"
            target_id = f"func:file_{file_idx}:func_{func_idx + 1}"
            call_edge = CallEdge(source_id, target_id, call_site=func_idx * 10 + 5)
            graph.add_edge(call_edge)
    
    # Add some cross-file calls
    for file_idx in range(9):
        source_id = f"func:file_{file_idx}:func_50"
        target_id = f"func:file_{file_idx + 1}:func_0"
        call_edge = CallEdge(source_id, target_id, call_site=505)
        graph.add_edge(call_edge)
    
    # Add inheritance edges between classes
    for file_idx in range(10):
        for class_idx in range(9):
            source_id = f"class:file_{file_idx}:class_{class_idx}"
            target_id = f"class:file_{file_idx}:class_{class_idx + 1}"
            inherit_edge = InheritanceEdge(source_id, target_id)
            graph.add_edge(inherit_edge)
    
    return graph


@pytest.fixture
def mock_storage_with_graph(large_graph):
    """Create mock storage adapter with large graph data."""
    mock_storage = Mock(spec=StorageAdapter)
    
    # Mock query_nodes to return filtered results
    def mock_query_nodes(node_type, filters, limit=100, offset=0):
        nodes = large_graph.get_nodes_by_type(node_type)
        
        # Apply filters
        filtered_nodes = []
        for node in nodes:
            include = True
            for key, value in filters.items():
                if key in ('limit', 'offset'):
                    continue
                
                node_value = node.properties.get(key)
                if isinstance(value, dict):
                    for op, op_value in value.items():
                        if op == '$gt' and (node_value is None or node_value <= op_value):
                            include = False
                        elif op == '$lt' and (node_value is None or node_value >= op_value):
                            include = False
                        elif op == '$gte' and (node_value is None or node_value < op_value):
                            include = False
                        elif op == '$lte' and (node_value is None or node_value > op_value):
                            include = False
                else:
                    if node_value != value:
                        include = False
                
                if not include:
                    break
            
            if include:
                filtered_nodes.append(node)
        
        # Apply pagination
        start_idx = offset
        end_idx = offset + limit
        return filtered_nodes[start_idx:end_idx]
    
    # Mock get_edges to return edges from graph
    def mock_get_edges(source, target=None, edge_type=None):
        edges = large_graph.get_outgoing_edges(source, edge_type)
        if target:
            edges = [e for e in edges if e.target == target]
        return edges
    
    mock_storage.query_nodes.side_effect = mock_query_nodes
    mock_storage.get_edges.side_effect = mock_get_edges
    
    return mock_storage


class TestGraphSerializationPerformance:
    """Test graph serialization performance."""
    
    def test_json_serialization_performance(self, large_graph):
        """Test JSON serialization performance."""
        # Measure serialization time
        start_time = time.time()
        json_data = large_graph.to_json()
        serialize_time = time.time() - start_time
        
        # Measure deserialization time
        start_time = time.time()
        restored_graph = Graph.from_json(json_data)
        deserialize_time = time.time() - start_time
        
        # Performance assertions
        assert serialize_time < 1.0  # Should serialize in < 1 second
        assert deserialize_time < 1.0  # Should deserialize in < 1 second
        
        # Verify data integrity
        assert len(restored_graph.nodes) == len(large_graph.nodes)
        assert len(restored_graph.edges) == len(large_graph.edges)
        
        print(f"JSON Serialization: {serialize_time:.3f}s")
        print(f"JSON Deserialization: {deserialize_time:.3f}s")
        print(f"JSON Size: {len(json_data)} bytes")
    
    def test_msgpack_serialization_performance(self, large_graph):
        """Test MessagePack serialization performance."""
        # Measure serialization time
        start_time = time.time()
        msgpack_data = large_graph.to_msgpack()
        serialize_time = time.time() - start_time
        
        # Measure deserialization time
        start_time = time.time()
        restored_graph = Graph.from_msgpack(msgpack_data)
        deserialize_time = time.time() - start_time
        
        # Performance assertions
        assert serialize_time < 0.5  # MessagePack should be faster than JSON
        assert deserialize_time < 0.5
        
        # Verify data integrity
        assert len(restored_graph.nodes) == len(large_graph.nodes)
        assert len(restored_graph.edges) == len(large_graph.edges)
        
        print(f"MessagePack Serialization: {serialize_time:.3f}s")
        print(f"MessagePack Deserialization: {deserialize_time:.3f}s")
        print(f"MessagePack Size: {len(msgpack_data)} bytes")
    
    def test_serialization_comparison(self, large_graph):
        """Compare JSON vs MessagePack serialization."""
        # JSON
        start_time = time.time()
        json_data = large_graph.to_json()
        json_time = time.time() - start_time
        
        # MessagePack
        start_time = time.time()
        msgpack_data = large_graph.to_msgpack()
        msgpack_time = time.time() - start_time
        
        # MessagePack should be faster and more compact
        assert msgpack_time < json_time
        assert len(msgpack_data) < len(json_data)
        
        print(f"JSON: {json_time:.3f}s, {len(json_data)} bytes")
        print(f"MessagePack: {msgpack_time:.3f}s, {len(msgpack_data)} bytes")
        print(f"MessagePack is {json_time/msgpack_time:.1f}x faster")
        print(f"MessagePack is {len(json_data)/len(msgpack_data):.1f}x more compact")


class TestGraphTraversalPerformance:
    """Test graph traversal performance."""
    
    def test_bfs_traversal_performance(self, large_graph):
        """Test BFS traversal performance."""
        # Get a file node as starting point
        file_nodes = large_graph.get_nodes_by_type('file')
        start_node = file_nodes[0].id
        
        # Measure BFS traversal time
        start_time = time.time()
        traversal_result = list(large_graph.traverse_bfs(start_node, max_depth=5))
        traversal_time = time.time() - start_time
        
        # Performance assertion
        assert traversal_time < 0.1  # Should traverse in < 100ms
        
        # Verify traversal found nodes
        assert len(traversal_result) > 0
        
        print(f"BFS Traversal: {traversal_time:.3f}s, {len(traversal_result)} nodes")
    
    def test_dfs_traversal_performance(self, large_graph):
        """Test DFS traversal performance."""
        # Get a file node as starting point
        file_nodes = large_graph.get_nodes_by_type('file')
        start_node = file_nodes[0].id
        
        # Measure DFS traversal time
        start_time = time.time()
        traversal_result = list(large_graph.traverse_dfs(start_node, max_depth=5))
        traversal_time = time.time() - start_time
        
        # Performance assertion
        assert traversal_time < 0.1  # Should traverse in < 100ms
        
        # Verify traversal found nodes
        assert len(traversal_result) > 0
        
        print(f"DFS Traversal: {traversal_time:.3f}s, {len(traversal_result)} nodes")
    
    def test_neighbor_lookup_performance(self, large_graph):
        """Test neighbor lookup performance."""
        # Get function nodes
        function_nodes = large_graph.get_nodes_by_type('function')
        
        # Measure neighbor lookup times
        times = []
        for i in range(100):  # Test 100 random nodes
            node = function_nodes[i]
            start_time = time.time()
            neighbors = large_graph.get_neighbors(node.id)
            lookup_time = time.time() - start_time
            times.append(lookup_time)
        
        # Calculate statistics
        avg_time = statistics.mean(times)
        max_time = max(times)
        
        # Performance assertions
        assert avg_time < 0.001  # Average lookup < 1ms
        assert max_time < 0.01   # Max lookup < 10ms
        
        print(f"Neighbor Lookup - Avg: {avg_time*1000:.3f}ms, Max: {max_time*1000:.3f}ms")


class TestQueryPerformance:
    """Test query performance."""
    
    def test_simple_query_performance(self, mock_storage_with_graph):
        """Test simple query performance."""
        processor = QueryProcessor(mock_storage_with_graph)
        
        # Test simple type query
        query = "FIND function"
        ast = parse_query(query)
        
        # Measure query execution time
        start_time = time.time()
        result = processor.execute(ast)
        query_time = time.time() - start_time
        
        # Performance assertion
        assert query_time < 0.1  # Should execute in < 100ms
        assert len(result.nodes) > 0
        
        print(f"Simple Query: {query_time:.3f}s, {len(result.nodes)} results")
    
    def test_filtered_query_performance(self, mock_storage_with_graph):
        """Test filtered query performance."""
        processor = QueryProcessor(mock_storage_with_graph)
        
        # Test query with filters
        query = "FIND function WHERE complexity > 10"
        ast = parse_query(query)
        
        # Measure query execution time
        start_time = time.time()
        result = processor.execute(ast)
        query_time = time.time() - start_time
        
        # Performance assertion
        assert query_time < 0.2  # Should execute in < 200ms
        
        # Verify filtering worked
        for node in result.nodes:
            assert node.complexity > 10
        
        print(f"Filtered Query: {query_time:.3f}s, {len(result.nodes)} results")
    
    def test_complex_query_performance(self, mock_storage_with_graph):
        """Test complex query performance."""
        processor = QueryProcessor(mock_storage_with_graph)
        
        # Test complex query with multiple conditions
        query = "FIND function WHERE complexity > 5 AND complexity < 15"
        ast = parse_query(query)
        
        # Measure query execution time
        start_time = time.time()
        result = processor.execute(ast)
        query_time = time.time() - start_time
        
        # Performance assertion
        assert query_time < 0.3  # Should execute in < 300ms
        
        # Verify filtering worked
        for node in result.nodes:
            assert 5 < node.complexity < 15
        
        print(f"Complex Query: {query_time:.3f}s, {len(result.nodes)} results")
    
    def test_query_with_limit_performance(self, mock_storage_with_graph):
        """Test query with limit performance."""
        processor = QueryProcessor(mock_storage_with_graph)
        
        # Test query with limit
        query = "FIND function LIMIT 50"
        ast = parse_query(query)
        
        # Measure query execution time
        start_time = time.time()
        result = processor.execute(ast)
        query_time = time.time() - start_time
        
        # Performance assertion
        assert query_time < 0.1  # Should execute in < 100ms
        assert len(result.nodes) <= 50
        
        print(f"Limited Query: {query_time:.3f}s, {len(result.nodes)} results")
    
    def test_convenience_method_performance(self, mock_storage_with_graph):
        """Test convenience method performance."""
        processor = QueryProcessor(mock_storage_with_graph)
        
        # Test find_high_complexity_functions
        start_time = time.time()
        result = processor.find_high_complexity_functions(threshold=15)
        query_time = time.time() - start_time
        
        # Performance assertion
        assert query_time < 0.2  # Should execute in < 200ms
        
        # Verify results
        for node in result:
            assert node.complexity > 15
        
        print(f"Convenience Method: {query_time:.3f}s, {len(result)} results")


class TestMemoryUsage:
    """Test memory usage of graph operations."""
    
    def test_graph_memory_usage(self, large_graph):
        """Test memory usage of large graph."""
        import sys
        
        # Measure graph size in memory
        graph_size = sys.getsizeof(large_graph)
        nodes_size = sum(sys.getsizeof(node) for node in large_graph.nodes.values())
        edges_size = sum(sys.getsizeof(edge) for edge in large_graph.edges)
        
        total_size = graph_size + nodes_size + edges_size
        
        # Memory usage should be reasonable
        # For ~1100 nodes and ~1000 edges, should be < 10MB
        assert total_size < 10 * 1024 * 1024  # 10MB
        
        print(f"Graph Memory Usage:")
        print(f"  Graph object: {graph_size:,} bytes")
        print(f"  Nodes: {nodes_size:,} bytes")
        print(f"  Edges: {edges_size:,} bytes")
        print(f"  Total: {total_size:,} bytes")
        print(f"  Per node: {total_size // len(large_graph.nodes):,} bytes")


class TestScalabilityBenchmarks:
    """Scalability benchmarks for different graph sizes."""
    
    def create_graph_of_size(self, num_files, funcs_per_file):
        """Create graph of specified size."""
        graph = Graph()
        
        for file_idx in range(num_files):
            file_node = FileNode(
                id=f"file:bench_{file_idx}.py",
                path=f"/bench/file_{file_idx}.py",
                language="python",
                loc=100
            )
            graph.add_node(file_node)
            
            for func_idx in range(funcs_per_file):
                func_node = FunctionNode(
                    id=f"func:bench_{file_idx}:func_{func_idx}",
                    name=f"func_{func_idx}",
                    qualified_name=f"bench_{file_idx}.func_{func_idx}",
                    line_start=func_idx * 10,
                    line_end=(func_idx * 10) + 9,
                    complexity=(func_idx % 10) + 1
                )
                graph.add_node(func_node)
                
                # Add contains edge
                contains_edge = ContainsEdge(file_node.id, func_node.id)
                graph.add_edge(contains_edge)
                
                # Add call edge to next function
                if func_idx < funcs_per_file - 1:
                    next_func_id = f"func:bench_{file_idx}:func_{func_idx + 1}"
                    call_edge = CallEdge(func_node.id, next_func_id)
                    graph.add_edge(call_edge)
        
        return graph
    
    def test_serialization_scalability(self):
        """Test serialization performance across different graph sizes."""
        sizes = [(1, 100), (5, 100), (10, 100), (20, 100)]  # (files, funcs_per_file)
        
        print("\nSerialization Scalability:")
        print("Nodes\tEdges\tJSON(ms)\tMsgPack(ms)")
        
        for num_files, funcs_per_file in sizes:
            graph = self.create_graph_of_size(num_files, funcs_per_file)
            
            # JSON serialization
            start_time = time.time()
            json_data = graph.to_json()
            json_time = (time.time() - start_time) * 1000
            
            # MessagePack serialization
            start_time = time.time()
            msgpack_data = graph.to_msgpack()
            msgpack_time = (time.time() - start_time) * 1000
            
            num_nodes = len(graph.nodes)
            num_edges = len(graph.edges)
            
            print(f"{num_nodes}\t{num_edges}\t{json_time:.1f}\t\t{msgpack_time:.1f}")
            
            # Performance should scale reasonably
            assert json_time < num_nodes * 0.1  # < 0.1ms per node
            assert msgpack_time < num_nodes * 0.05  # < 0.05ms per node
    
    def test_traversal_scalability(self):
        """Test traversal performance across different graph sizes."""
        sizes = [(1, 50), (1, 100), (1, 200), (1, 500)]  # (files, funcs_per_file)
        
        print("\nTraversal Scalability:")
        print("Nodes\tBFS(ms)\tDFS(ms)")
        
        for num_files, funcs_per_file in sizes:
            graph = self.create_graph_of_size(num_files, funcs_per_file)
            start_node = f"file:bench_0.py"
            
            # BFS traversal
            start_time = time.time()
            bfs_result = list(graph.traverse_bfs(start_node, max_depth=10))
            bfs_time = (time.time() - start_time) * 1000
            
            # DFS traversal
            start_time = time.time()
            dfs_result = list(graph.traverse_dfs(start_node, max_depth=10))
            dfs_time = (time.time() - start_time) * 1000
            
            num_nodes = len(graph.nodes)
            
            print(f"{num_nodes}\t{bfs_time:.1f}\t{dfs_time:.1f}")
            
            # Performance should scale reasonably
            assert bfs_time < num_nodes * 0.01  # < 0.01ms per node
            assert dfs_time < num_nodes * 0.01  # < 0.01ms per node


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])