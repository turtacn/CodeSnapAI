"""
Abstract storage adapter interface for semantic graphs.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Iterator, ContextManager
from contextlib import contextmanager

from ..models.graph import Graph
from ..models.node import Node
from ..models.edge import Edge


class StorageException(Exception):
    """Base exception for storage operations."""
    pass


class NodeNotFoundError(StorageException):
    """Raised when a requested node is not found."""
    pass


class StorageAdapter(ABC):
    """Abstract base class for graph storage adapters."""
    
    @abstractmethod
    def save_graph(self, graph: Graph, **kwargs) -> None:
        """
        Save a complete graph to storage.
        
        Args:
            graph: The graph to save
            **kwargs: Implementation-specific options (e.g., ttl for Redis)
        
        Raises:
            StorageException: If save operation fails
        """
        pass
    
    @abstractmethod
    def load_graph(self, root_node_id: str, max_depth: int = 10) -> Graph:
        """
        Load a graph starting from a root node.
        
        Args:
            root_node_id: ID of the root node to start traversal
            max_depth: Maximum depth for graph traversal
            
        Returns:
            Graph: The loaded graph
            
        Raises:
            NodeNotFoundError: If root node is not found
            StorageException: If load operation fails
        """
        pass
    
    @abstractmethod
    def query_nodes(self, node_type: str, filters: Dict[str, Any], 
                   limit: int = 100, offset: int = 0) -> List[Node]:
        """
        Query nodes by type and filters.
        
        Args:
            node_type: Type of nodes to query (function, class, etc.)
            filters: Dictionary of property filters
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List[Node]: Matching nodes
            
        Raises:
            StorageException: If query operation fails
        """
        pass
    
    @abstractmethod
    def save_node(self, node: Node) -> None:
        """
        Save a single node to storage.
        
        Args:
            node: The node to save
            
        Raises:
            StorageException: If save operation fails
        """
        pass
    
    @abstractmethod
    def save_edge(self, edge: Edge) -> None:
        """
        Save a single edge to storage.
        
        Args:
            edge: The edge to save
            
        Raises:
            StorageException: If save operation fails
        """
        pass
    
    @abstractmethod
    def delete_node(self, node_id: str) -> None:
        """
        Delete a node and all its edges from storage.
        
        Args:
            node_id: ID of the node to delete
            
        Raises:
            StorageException: If delete operation fails
        """
        pass
    
    @abstractmethod
    def delete_edge(self, source: str, target: str, edge_type: Optional[str] = None) -> None:
        """
        Delete edge(s) between two nodes.
        
        Args:
            source: Source node ID
            target: Target node ID
            edge_type: Optional edge type filter
            
        Raises:
            StorageException: If delete operation fails
        """
        pass
    
    @abstractmethod
    def get_node(self, node_id: str) -> Node:
        """
        Get a single node by ID.
        
        Args:
            node_id: ID of the node to retrieve
            
        Returns:
            Node: The requested node
            
        Raises:
            NodeNotFoundError: If node is not found
            StorageException: If get operation fails
        """
        pass
    
    @abstractmethod
    def get_edges(self, source: str, target: Optional[str] = None, 
                 edge_type: Optional[str] = None) -> List[Edge]:
        """
        Get edges from a source node.
        
        Args:
            source: Source node ID
            target: Optional target node ID filter
            edge_type: Optional edge type filter
            
        Returns:
            List[Edge]: Matching edges
            
        Raises:
            StorageException: If get operation fails
        """
        pass
    
    @abstractmethod
    def node_exists(self, node_id: str) -> bool:
        """
        Check if a node exists in storage.
        
        Args:
            node_id: ID of the node to check
            
        Returns:
            bool: True if node exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_node_count(self, node_type: Optional[str] = None) -> int:
        """
        Get count of nodes in storage.
        
        Args:
            node_type: Optional node type filter
            
        Returns:
            int: Number of nodes
        """
        pass
    
    @abstractmethod
    def get_edge_count(self, edge_type: Optional[str] = None) -> int:
        """
        Get count of edges in storage.
        
        Args:
            edge_type: Optional edge type filter
            
        Returns:
            int: Number of edges
        """
        pass
    
    @abstractmethod
    @contextmanager
    def transaction(self) -> ContextManager[None]:
        """
        Create a transaction context for atomic operations.
        
        Yields:
            None
            
        Raises:
            StorageException: If transaction fails
        """
        pass
    
    def bulk_save_nodes(self, nodes: List[Node], batch_size: int = 1000) -> None:
        """
        Save multiple nodes in batches.
        
        Args:
            nodes: List of nodes to save
            batch_size: Number of nodes per batch
            
        Raises:
            StorageException: If bulk save operation fails
        """
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]
            with self.transaction():
                for node in batch:
                    self.save_node(node)
    
    def bulk_save_edges(self, edges: List[Edge], batch_size: int = 1000) -> None:
        """
        Save multiple edges in batches.
        
        Args:
            edges: List of edges to save
            batch_size: Number of edges per batch
            
        Raises:
            StorageException: If bulk save operation fails
        """
        for i in range(0, len(edges), batch_size):
            batch = edges[i:i + batch_size]
            with self.transaction():
                for edge in batch:
                    self.save_edge(edge)
    
    def clear_all(self) -> None:
        """
        Clear all data from storage.
        
        Warning: This operation is irreversible!
        
        Raises:
            StorageException: If clear operation fails
        """
        raise NotImplementedError("clear_all must be implemented by subclasses")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dict[str, Any]: Statistics about stored data
        """
        return {
            'total_nodes': self.get_node_count(),
            'total_edges': self.get_edge_count(),
            'node_types': {},  # Could be implemented by subclasses
            'edge_types': {}   # Could be implemented by subclasses
        }