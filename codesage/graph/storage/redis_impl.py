"""
Redis storage adapter implementation.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Set
from contextlib import contextmanager
from collections import defaultdict

import redis
import msgpack

from .adapter import StorageAdapter, StorageException, NodeNotFoundError
from ..models.graph import Graph
from ..models.node import Node
from ..models.edge import Edge

logger = logging.getLogger(__name__)


class RedisConfig:
    """Configuration for Redis storage adapter."""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0,
                 password: Optional[str] = None, socket_timeout: int = 5,
                 max_connections: int = 50, key_prefix: str = 'codesage:graph',
                 default_ttl: int = 3600):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.socket_timeout = socket_timeout
        self.max_connections = max_connections
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl


class RedisStorageAdapter(StorageAdapter):
    """Redis implementation of storage adapter."""
    
    def __init__(self, config: RedisConfig):
        """Initialize Redis storage adapter."""
        self.config = config
        self.redis = self._create_redis_client()
        self._verify_connection()
        
        # Transaction state
        self._transaction_pipeline = None
    
    def _create_redis_client(self) -> redis.Redis:
        """Create Redis client with connection pool."""
        pool = redis.ConnectionPool(
            host=self.config.host,
            port=self.config.port,
            db=self.config.db,
            password=self.config.password,
            socket_timeout=self.config.socket_timeout,
            socket_connect_timeout=self.config.socket_timeout,
            socket_keepalive=True,
            max_connections=self.config.max_connections,
            retry_on_timeout=True
        )
        return redis.Redis(connection_pool=pool, decode_responses=False)
    
    def _verify_connection(self) -> None:
        """Verify Redis connection."""
        try:
            self.redis.ping()
            logger.info(f"Connected to Redis at {self.config.host}:{self.config.port}")
        except redis.RedisError as e:
            raise StorageException(f"Failed to connect to Redis: {e}")
    
    def _get_node_key(self, node_id: str) -> str:
        """Get Redis key for a node."""
        return f"{self.config.key_prefix}:node:{node_id}"
    
    def _get_edges_key(self, source_id: str) -> str:
        """Get Redis key for edges from a source node."""
        return f"{self.config.key_prefix}:edges:{source_id}"
    
    def _get_node_type_key(self, node_type: str) -> str:
        """Get Redis key for nodes of a specific type."""
        return f"{self.config.key_prefix}:type:{node_type}"
    
    def _get_edge_type_key(self, edge_type: str) -> str:
        """Get Redis key for edges of a specific type."""
        return f"{self.config.key_prefix}:edge_type:{edge_type}"
    
    def _serialize_node(self, node: Node) -> bytes:
        """Serialize node to bytes using MessagePack."""
        return msgpack.packb(node.to_dict())
    
    def _deserialize_node(self, data: bytes) -> Node:
        """Deserialize node from bytes."""
        node_dict = msgpack.unpackb(data, raw=False)
        return Node.from_dict(node_dict)
    
    def _serialize_edge(self, edge: Edge) -> bytes:
        """Serialize edge to bytes using MessagePack."""
        return msgpack.packb(edge.to_dict())
    
    def _deserialize_edge(self, data: bytes) -> Edge:
        """Deserialize edge from bytes."""
        edge_dict = msgpack.unpackb(data, raw=False)
        return Edge.from_dict(edge_dict)
    
    def _execute_command(self, func, *args, **kwargs):
        """Execute Redis command with error handling."""
        try:
            if self._transaction_pipeline:
                return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except redis.RedisError as e:
            raise StorageException(f"Redis operation failed: {e}")
    
    def save_graph(self, graph: Graph, ttl: Optional[int] = None) -> None:
        """Save complete graph to Redis using pipeline."""
        if ttl is None:
            ttl = self.config.default_ttl
        
        try:
            pipe = self.redis.pipeline()
            
            # Save all nodes
            for node in graph.nodes.values():
                node_key = self._get_node_key(node.id)
                node_data = self._serialize_node(node)
                
                pipe.set(node_key, node_data)
                if ttl > 0:
                    pipe.expire(node_key, ttl)
                
                # Add to node type index
                type_key = self._get_node_type_key(node.type)
                pipe.sadd(type_key, node.id)
                if ttl > 0:
                    pipe.expire(type_key, ttl)
            
            # Save all edges (grouped by source)
            edges_by_source = defaultdict(list)
            for edge in graph.edges:
                edges_by_source[edge.source].append(edge)
            
            for source_id, edges in edges_by_source.items():
                edges_key = self._get_edges_key(source_id)
                
                # Store edges as a hash: target_id -> edge_data
                edge_mapping = {}
                for edge in edges:
                    edge_key = f"{edge.target}:{edge.type}"
                    edge_data = self._serialize_edge(edge)
                    edge_mapping[edge_key] = edge_data
                    
                    # Add to edge type index
                    edge_type_key = self._get_edge_type_key(edge.type)
                    pipe.sadd(edge_type_key, f"{edge.source}:{edge.target}")
                    if ttl > 0:
                        pipe.expire(edge_type_key, ttl)
                
                if edge_mapping:
                    pipe.hset(edges_key, mapping=edge_mapping)
                    if ttl > 0:
                        pipe.expire(edges_key, ttl)
            
            # Execute pipeline
            pipe.execute()
            
            logger.info(f"Saved graph to Redis: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
            
        except redis.RedisError as e:
            raise StorageException(f"Failed to save graph to Redis: {e}")
    
    def load_graph(self, root_node_id: str, max_depth: int = 10) -> Graph:
        """Load graph using BFS traversal from root node."""
        graph = Graph()
        visited = set()
        queue = [(root_node_id, 0)]
        
        try:
            while queue:
                node_id, depth = queue.pop(0)
                
                if node_id in visited or depth > max_depth:
                    continue
                
                visited.add(node_id)
                
                # Load node
                node_key = self._get_node_key(node_id)
                node_data = self.redis.get(node_key)
                
                if not node_data:
                    if depth == 0:  # Root node not found
                        raise NodeNotFoundError(f"Root node not found: {node_id}")
                    continue
                
                node = self._deserialize_node(node_data)
                graph.add_node(node)
                
                # Load outgoing edges
                edges_key = self._get_edges_key(node_id)
                edge_data = self.redis.hgetall(edges_key)
                
                for edge_key, edge_bytes in edge_data.items():
                    edge_key_str = edge_key.decode('utf-8') if isinstance(edge_key, bytes) else edge_key
                    edge = self._deserialize_edge(edge_bytes)
                    
                    # Add target to queue for next level
                    if edge.target not in visited:
                        queue.append((edge.target, depth + 1))
                    
                    # We'll add the edge after loading the target node
                    if graph.has_node(edge.target):
                        graph.add_edge(edge)
                    else:
                        # Store edge for later addition
                        if not hasattr(graph, '_pending_edges'):
                            graph._pending_edges = []
                        graph._pending_edges.append(edge)
            
            # Add any pending edges
            if hasattr(graph, '_pending_edges'):
                for edge in graph._pending_edges:
                    if graph.has_node(edge.source) and graph.has_node(edge.target):
                        graph.add_edge(edge)
                delattr(graph, '_pending_edges')
            
            logger.info(f"Loaded graph from Redis: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
            return graph
            
        except redis.RedisError as e:
            raise StorageException(f"Failed to load graph from Redis: {e}")
    
    def query_nodes(self, node_type: str, filters: Dict[str, Any], 
                   limit: int = 100, offset: int = 0) -> List[Node]:
        """Query nodes by type and filters."""
        try:
            # Get all node IDs of the specified type
            type_key = self._get_node_type_key(node_type)
            node_ids = self.redis.smembers(type_key)
            
            if not node_ids:
                return []
            
            # Convert bytes to strings
            node_ids = [nid.decode('utf-8') if isinstance(nid, bytes) else nid for nid in node_ids]
            
            # Load nodes in batches
            results = []
            batch_size = 100
            
            for i in range(0, len(node_ids), batch_size):
                batch_ids = node_ids[i:i + batch_size]
                node_keys = [self._get_node_key(nid) for nid in batch_ids]
                
                # Use mget for batch loading
                node_data_list = self.redis.mget(node_keys)
                
                for node_data in node_data_list:
                    if not node_data:
                        continue
                    
                    node = self._deserialize_node(node_data)
                    
                    # Apply filters
                    if self._apply_filters(node, filters):
                        results.append(node)
            
            # Apply pagination
            start_idx = offset
            end_idx = offset + limit
            return results[start_idx:end_idx]
            
        except redis.RedisError as e:
            raise StorageException(f"Failed to query nodes from Redis: {e}")
    
    def _apply_filters(self, node: Node, filters: Dict[str, Any]) -> bool:
        """Apply filters to a node."""
        for key, value in filters.items():
            if key == 'limit' or key == 'offset':
                continue
            
            node_value = node.properties.get(key)
            
            if isinstance(value, dict):
                # Range queries: {'complexity': {'$gt': 10}}
                for op, op_value in value.items():
                    if op == '$gt' and (node_value is None or node_value <= op_value):
                        return False
                    elif op == '$gte' and (node_value is None or node_value < op_value):
                        return False
                    elif op == '$lt' and (node_value is None or node_value >= op_value):
                        return False
                    elif op == '$lte' and (node_value is None or node_value > op_value):
                        return False
                    elif op == '$ne' and node_value == op_value:
                        return False
            else:
                # Exact match
                if node_value != value:
                    return False
        
        return True
    
    def save_node(self, node: Node) -> None:
        """Save a single node."""
        try:
            node_key = self._get_node_key(node.id)
            node_data = self._serialize_node(node)
            
            client = self._transaction_pipeline or self.redis
            client.set(node_key, node_data)
            client.expire(node_key, self.config.default_ttl)
            
            # Add to type index
            type_key = self._get_node_type_key(node.type)
            client.sadd(type_key, node.id)
            client.expire(type_key, self.config.default_ttl)
            
        except redis.RedisError as e:
            raise StorageException(f"Failed to save node to Redis: {e}")
    
    def save_edge(self, edge: Edge) -> None:
        """Save a single edge."""
        try:
            edges_key = self._get_edges_key(edge.source)
            edge_key = f"{edge.target}:{edge.type}"
            edge_data = self._serialize_edge(edge)
            
            client = self._transaction_pipeline or self.redis
            client.hset(edges_key, edge_key, edge_data)
            client.expire(edges_key, self.config.default_ttl)
            
            # Add to edge type index
            edge_type_key = self._get_edge_type_key(edge.type)
            client.sadd(edge_type_key, f"{edge.source}:{edge.target}")
            client.expire(edge_type_key, self.config.default_ttl)
            
        except redis.RedisError as e:
            raise StorageException(f"Failed to save edge to Redis: {e}")
    
    def delete_node(self, node_id: str) -> None:
        """Delete a node and all its edges."""
        try:
            client = self._transaction_pipeline or self.redis
            
            # Get node to find its type
            node_key = self._get_node_key(node_id)
            node_data = client.get(node_key)
            
            if node_data:
                node = self._deserialize_node(node_data)
                
                # Remove from type index
                type_key = self._get_node_type_key(node.type)
                client.srem(type_key, node_id)
            
            # Delete node
            client.delete(node_key)
            
            # Delete outgoing edges
            edges_key = self._get_edges_key(node_id)
            client.delete(edges_key)
            
            # TODO: Delete incoming edges (would require scanning all edge keys)
            # This is a limitation of the current Redis schema design
            
        except redis.RedisError as e:
            raise StorageException(f"Failed to delete node from Redis: {e}")
    
    def delete_edge(self, source: str, target: str, edge_type: Optional[str] = None) -> None:
        """Delete edge(s) between two nodes."""
        try:
            edges_key = self._get_edges_key(source)
            client = self._transaction_pipeline or self.redis
            
            if edge_type:
                # Delete specific edge type
                edge_key = f"{target}:{edge_type}"
                client.hdel(edges_key, edge_key)
                
                # Remove from edge type index
                edge_type_key = self._get_edge_type_key(edge_type)
                client.srem(edge_type_key, f"{source}:{target}")
            else:
                # Delete all edges to target
                edge_data = client.hgetall(edges_key)
                for edge_key in edge_data.keys():
                    edge_key_str = edge_key.decode('utf-8') if isinstance(edge_key, bytes) else edge_key
                    if edge_key_str.startswith(f"{target}:"):
                        client.hdel(edges_key, edge_key)
            
        except redis.RedisError as e:
            raise StorageException(f"Failed to delete edge from Redis: {e}")
    
    def get_node(self, node_id: str) -> Node:
        """Get a single node by ID."""
        try:
            node_key = self._get_node_key(node_id)
            node_data = self.redis.get(node_key)
            
            if not node_data:
                raise NodeNotFoundError(f"Node not found: {node_id}")
            
            return self._deserialize_node(node_data)
            
        except redis.RedisError as e:
            raise StorageException(f"Failed to get node from Redis: {e}")
    
    def get_edges(self, source: str, target: Optional[str] = None, 
                 edge_type: Optional[str] = None) -> List[Edge]:
        """Get edges from a source node."""
        try:
            edges_key = self._get_edges_key(source)
            edge_data = self.redis.hgetall(edges_key)
            
            edges = []
            for edge_key, edge_bytes in edge_data.items():
                edge_key_str = edge_key.decode('utf-8') if isinstance(edge_key, bytes) else edge_key
                edge = self._deserialize_edge(edge_bytes)
                
                # Apply filters
                if target and edge.target != target:
                    continue
                if edge_type and edge.type != edge_type:
                    continue
                
                edges.append(edge)
            
            return edges
            
        except redis.RedisError as e:
            raise StorageException(f"Failed to get edges from Redis: {e}")
    
    def node_exists(self, node_id: str) -> bool:
        """Check if a node exists."""
        try:
            node_key = self._get_node_key(node_id)
            return self.redis.exists(node_key) > 0
        except redis.RedisError as e:
            raise StorageException(f"Failed to check node existence in Redis: {e}")
    
    def get_node_count(self, node_type: Optional[str] = None) -> int:
        """Get count of nodes."""
        try:
            if node_type:
                type_key = self._get_node_type_key(node_type)
                return self.redis.scard(type_key)
            else:
                # Count all node keys
                pattern = f"{self.config.key_prefix}:node:*"
                return len(self.redis.keys(pattern))
        except redis.RedisError as e:
            raise StorageException(f"Failed to get node count from Redis: {e}")
    
    def get_edge_count(self, edge_type: Optional[str] = None) -> int:
        """Get count of edges."""
        try:
            if edge_type:
                edge_type_key = self._get_edge_type_key(edge_type)
                return self.redis.scard(edge_type_key)
            else:
                # Count all edge keys
                pattern = f"{self.config.key_prefix}:edges:*"
                edge_keys = self.redis.keys(pattern)
                total = 0
                for key in edge_keys:
                    total += self.redis.hlen(key)
                return total
        except redis.RedisError as e:
            raise StorageException(f"Failed to get edge count from Redis: {e}")
    
    @contextmanager
    def transaction(self):
        """Create a Redis pipeline transaction."""
        if self._transaction_pipeline:
            # Nested transaction - just yield
            yield
        else:
            pipe = self.redis.pipeline()
            self._transaction_pipeline = pipe
            try:
                yield
                pipe.execute()
            except Exception as e:
                # Pipeline automatically discards on exception
                raise StorageException(f"Transaction failed: {e}")
            finally:
                self._transaction_pipeline = None
    
    def clear_all(self) -> None:
        """Clear all graph data from Redis."""
        try:
            pattern = f"{self.config.key_prefix}:*"
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
            logger.info("Cleared all graph data from Redis")
        except redis.RedisError as e:
            raise StorageException(f"Failed to clear Redis data: {e}")