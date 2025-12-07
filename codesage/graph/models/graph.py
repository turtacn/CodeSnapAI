"""
Graph data structure and delta operations.
"""

from typing import Dict, Set, List, Optional, Iterator, Tuple
from collections import defaultdict
import json
import msgpack

from .node import Node
from .edge import Edge


class Graph:
    """Represents a semantic graph of code entities and their relationships."""
    
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: Set[Edge] = set()
        self._outgoing_edges: Dict[str, Set[Edge]] = defaultdict(set)
        self._incoming_edges: Dict[str, Set[Edge]] = defaultdict(set)
    
    def add_node(self, node: Node) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node
    
    def remove_node(self, node_id: str) -> None:
        """Remove a node and all its edges from the graph."""
        if node_id not in self.nodes:
            return
        
        # Remove all edges connected to this node
        edges_to_remove = set()
        for edge in self.edges:
            if edge.source == node_id or edge.target == node_id:
                edges_to_remove.add(edge)
        
        for edge in edges_to_remove:
            self.remove_edge(edge)
        
        # Remove the node
        del self.nodes[node_id]
    
    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the graph."""
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise ValueError(f"Cannot add edge {edge.source} -> {edge.target}: nodes not found")
        
        self.edges.add(edge)
        self._outgoing_edges[edge.source].add(edge)
        self._incoming_edges[edge.target].add(edge)
    
    def remove_edge(self, edge: Edge) -> None:
        """Remove an edge from the graph."""
        if edge in self.edges:
            self.edges.remove(edge)
            self._outgoing_edges[edge.source].discard(edge)
            self._incoming_edges[edge.target].discard(edge)
    
    def has_node(self, node_id: str) -> bool:
        """Check if a node exists in the graph."""
        return node_id in self.nodes
    
    def has_edge(self, source: str, target: str, edge_type: Optional[str] = None) -> bool:
        """Check if an edge exists in the graph."""
        for edge in self._outgoing_edges[source]:
            if edge.target == target and (edge_type is None or edge.type == edge_type):
                return True
        return False
    
    def get_outgoing_edges(self, node_id: str, edge_type: Optional[str] = None) -> List[Edge]:
        """Get all outgoing edges from a node."""
        edges = list(self._outgoing_edges[node_id])
        if edge_type:
            edges = [e for e in edges if e.type == edge_type]
        return edges
    
    def get_incoming_edges(self, node_id: str, edge_type: Optional[str] = None) -> List[Edge]:
        """Get all incoming edges to a node."""
        edges = list(self._incoming_edges[node_id])
        if edge_type:
            edges = [e for e in edges if e.type == edge_type]
        return edges
    
    def get_neighbors(self, node_id: str, direction: str = 'both') -> Set[str]:
        """Get neighboring node IDs."""
        neighbors = set()
        
        if direction in ('out', 'both'):
            for edge in self._outgoing_edges[node_id]:
                neighbors.add(edge.target)
        
        if direction in ('in', 'both'):
            for edge in self._incoming_edges[node_id]:
                neighbors.add(edge.source)
        
        return neighbors
    
    def get_nodes_by_type(self, node_type: str) -> List[Node]:
        """Get all nodes of a specific type."""
        return [node for node in self.nodes.values() if node.type == node_type]
    
    def get_edges_by_type(self, edge_type: str) -> List[Edge]:
        """Get all edges of a specific type."""
        return [edge for edge in self.edges if edge.type == edge_type]
    
    def traverse_bfs(self, start_node_id: str, max_depth: int = 10) -> Iterator[Tuple[str, int]]:
        """Breadth-first traversal starting from a node."""
        if start_node_id not in self.nodes:
            return
        
        visited = set()
        queue = [(start_node_id, 0)]
        
        while queue:
            node_id, depth = queue.pop(0)
            
            if node_id in visited or depth > max_depth:
                continue
            
            visited.add(node_id)
            yield node_id, depth
            
            # Add neighbors to queue
            for neighbor_id in self.get_neighbors(node_id, 'out'):
                if neighbor_id not in visited:
                    queue.append((neighbor_id, depth + 1))
    
    def traverse_dfs(self, start_node_id: str, max_depth: int = 10) -> Iterator[Tuple[str, int]]:
        """Depth-first traversal starting from a node."""
        if start_node_id not in self.nodes:
            return
        
        visited = set()
        stack = [(start_node_id, 0)]
        
        while stack:
            node_id, depth = stack.pop()
            
            if node_id in visited or depth > max_depth:
                continue
            
            visited.add(node_id)
            yield node_id, depth
            
            # Add neighbors to stack (reverse order for consistent traversal)
            neighbors = list(self.get_neighbors(node_id, 'out'))
            for neighbor_id in reversed(neighbors):
                if neighbor_id not in visited:
                    stack.append((neighbor_id, depth + 1))
    
    def to_dict(self) -> Dict:
        """Convert graph to dictionary for serialization."""
        return {
            'nodes': {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            'edges': [edge.to_dict() for edge in self.edges]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Graph':
        """Create graph from dictionary."""
        graph = cls()
        
        # Add nodes
        for node_id, node_data in data['nodes'].items():
            node = Node.from_dict(node_data)
            graph.add_node(node)
        
        # Add edges
        for edge_data in data['edges']:
            edge = Edge.from_dict(edge_data)
            graph.add_edge(edge)
        
        return graph
    
    def to_json(self) -> str:
        """Serialize graph to JSON."""
        return json.dumps(self.to_dict(), indent=2)
    
    def to_msgpack(self) -> bytes:
        """Serialize graph to MessagePack."""
        return msgpack.packb(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Graph':
        """Deserialize graph from JSON."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_msgpack(cls, msgpack_data: bytes) -> 'Graph':
        """Deserialize graph from MessagePack."""
        data = msgpack.unpackb(msgpack_data, raw=False)
        return cls.from_dict(data)
    
    def __len__(self) -> int:
        """Return number of nodes in the graph."""
        return len(self.nodes)
    
    def __contains__(self, node_id: str) -> bool:
        """Check if node exists in graph."""
        return node_id in self.nodes
    
    def __str__(self) -> str:
        return f"Graph(nodes={len(self.nodes)}, edges={len(self.edges)})"


class GraphDelta:
    """Represents changes to be applied to a graph."""
    
    def __init__(self):
        self.added_nodes: List[Node] = []
        self.updated_nodes: List[Node] = []
        self.deleted_nodes: Set[str] = set()
        self.added_edges: List[Edge] = []
        self.deleted_edges: Set[Tuple[str, str, str]] = set()  # (source, target, type)
    
    def add_node(self, node: Node) -> None:
        """Mark a node for addition."""
        self.added_nodes.append(node)
    
    def update_node(self, node: Node) -> None:
        """Mark a node for update."""
        self.updated_nodes.append(node)
    
    def delete_node(self, node_id: str) -> None:
        """Mark a node for deletion."""
        self.deleted_nodes.add(node_id)
    
    def add_edge(self, edge: Edge) -> None:
        """Mark an edge for addition."""
        self.added_edges.append(edge)
    
    def delete_edge(self, source: str, target: str, edge_type: str = None) -> None:
        """Mark an edge for deletion."""
        # If edge_type is None, we'll delete all edges between source and target
        self.deleted_edges.add((source, target, edge_type or '*'))
    
    def has_changes(self) -> bool:
        """Check if delta contains any changes."""
        return (bool(self.added_nodes) or 
                bool(self.updated_nodes) or 
                bool(self.deleted_nodes) or 
                bool(self.added_edges) or 
                bool(self.deleted_edges))
    
    def apply_to(self, graph: Graph) -> None:
        """Apply this delta to a graph."""
        # Delete edges first (before deleting nodes)
        for source, target, edge_type in self.deleted_edges:
            if edge_type == '*':
                # Delete all edges between source and target
                edges_to_remove = []
                for edge in graph.edges:
                    if edge.source == source and edge.target == target:
                        edges_to_remove.append(edge)
                for edge in edges_to_remove:
                    graph.remove_edge(edge)
            else:
                # Delete specific edge type
                edges_to_remove = []
                for edge in graph.edges:
                    if (edge.source == source and 
                        edge.target == target and 
                        edge.type == edge_type):
                        edges_to_remove.append(edge)
                for edge in edges_to_remove:
                    graph.remove_edge(edge)
        
        # Delete nodes
        for node_id in self.deleted_nodes:
            graph.remove_node(node_id)
        
        # Add/update nodes
        for node in self.added_nodes + self.updated_nodes:
            graph.add_node(node)
        
        # Add edges
        for edge in self.added_edges:
            try:
                graph.add_edge(edge)
            except ValueError:
                # Skip edges where nodes don't exist
                pass
    
    def __str__(self) -> str:
        return (f"GraphDelta(+{len(self.added_nodes)} nodes, "
                f"~{len(self.updated_nodes)} nodes, "
                f"-{len(self.deleted_nodes)} nodes, "
                f"+{len(self.added_edges)} edges, "
                f"-{len(self.deleted_edges)} edges)")