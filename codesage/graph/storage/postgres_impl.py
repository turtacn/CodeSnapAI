"""
PostgreSQL storage adapter implementation.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import (
    create_engine, Column, String, Text, DateTime, Integer, Index,
    text, and_, or_, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .adapter import StorageAdapter, StorageException, NodeNotFoundError
from ..models.graph import Graph
from ..models.node import Node
from ..models.edge import Edge

logger = logging.getLogger(__name__)

Base = declarative_base()


class NodeTable(Base):
    """SQLAlchemy model for nodes table."""
    __tablename__ = 'nodes'
    
    id = Column(String(500), primary_key=True)
    type = Column(String(50), nullable=False, index=True)
    properties = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_nodes_type', 'type'),
        Index('idx_nodes_properties_gin', 'properties', postgresql_using='gin'),
    )


class EdgeTable(Base):
    """SQLAlchemy model for edges table."""
    __tablename__ = 'edges'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(500), nullable=False, index=True)
    target = Column(String(500), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)
    properties = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_edges_source', 'source'),
        Index('idx_edges_target', 'target'),
        Index('idx_edges_type', 'type'),
        Index('idx_edges_source_target', 'source', 'target'),
        Index('idx_edges_properties_gin', 'properties', postgresql_using='gin'),
    )


class PostgresConfig:
    """Configuration for PostgreSQL storage adapter."""
    
    def __init__(self, host: str = 'localhost', port: int = 5432,
                 database: str = 'codesage', username: str = 'codesage',
                 password: str = 'codesage', pool_size: int = 20,
                 max_overflow: int = 50, pool_timeout: int = 30,
                 pool_recycle: int = 3600, echo: bool = False):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo
    
    def get_connection_string(self) -> str:
        """Get SQLAlchemy connection string."""
        return (f"postgresql+psycopg2://{self.username}:{self.password}@"
                f"{self.host}:{self.port}/{self.database}")


class PostgreSQLStorageAdapter(StorageAdapter):
    """PostgreSQL implementation of storage adapter."""
    
    def __init__(self, config: PostgresConfig):
        """Initialize PostgreSQL storage adapter."""
        self.config = config
        self.engine = self._create_engine()
        self.session_factory = sessionmaker(bind=self.engine)
        self._create_tables()
        
        # Transaction state
        self._transaction_session = None
    
    def _create_engine(self):
        """Create SQLAlchemy engine."""
        connection_string = self.config.get_connection_string()
        
        engine = create_engine(
            connection_string,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            pool_timeout=self.config.pool_timeout,
            pool_recycle=self.config.pool_recycle,
            pool_pre_ping=True,
            echo=self.config.echo
        )
        
        logger.info(f"Created PostgreSQL engine for {self.config.host}:{self.config.port}")
        return engine
    
    def _create_tables(self):
        """Create tables if they don't exist."""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("PostgreSQL tables created/verified")
        except SQLAlchemyError as e:
            raise StorageException(f"Failed to create PostgreSQL tables: {e}")
    
    def _get_session(self) -> Session:
        """Get current session (transaction or new session)."""
        if self._transaction_session:
            return self._transaction_session
        return self.session_factory()
    
    def save_graph(self, graph: Graph, batch_size: int = 1000) -> None:
        """Save complete graph to PostgreSQL."""
        session = self._get_session()
        close_session = self._transaction_session is None
        
        try:
            # Prepare node data
            node_data = []
            for node in graph.nodes.values():
                node_data.append({
                    'id': node.id,
                    'type': node.type,
                    'properties': node.properties
                })
            
            # Prepare edge data
            edge_data = []
            for edge in graph.edges:
                edge_data.append({
                    'source': edge.source,
                    'target': edge.target,
                    'type': edge.type,
                    'properties': edge.properties
                })
            
            # Batch insert nodes
            if node_data:
                for i in range(0, len(node_data), batch_size):
                    batch = node_data[i:i + batch_size]
                    
                    # Use ON CONFLICT DO UPDATE for upsert
                    stmt = text("""
                        INSERT INTO nodes (id, type, properties, updated_at)
                        VALUES (:id, :type, :properties, NOW())
                        ON CONFLICT (id) DO UPDATE SET
                            type = EXCLUDED.type,
                            properties = EXCLUDED.properties,
                            updated_at = NOW()
                    """)
                    
                    session.execute(stmt, batch)
            
            # Batch insert edges
            if edge_data:
                for i in range(0, len(edge_data), batch_size):
                    batch = edge_data[i:i + batch_size]
                    
                    # Use ON CONFLICT DO NOTHING to avoid duplicates
                    stmt = text("""
                        INSERT INTO edges (source, target, type, properties)
                        VALUES (:source, :target, :type, :properties)
                        ON CONFLICT DO NOTHING
                    """)
                    
                    session.execute(stmt, batch)
            
            if close_session:
                session.commit()
            
            logger.info(f"Saved graph to PostgreSQL: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
            
        except SQLAlchemyError as e:
            if close_session:
                session.rollback()
            raise StorageException(f"Failed to save graph to PostgreSQL: {e}")
        finally:
            if close_session:
                session.close()
    
    def load_graph(self, root_node_id: str, max_depth: int = 10) -> Graph:
        """Load graph using recursive CTE."""
        session = self._get_session()
        close_session = self._transaction_session is None
        
        try:
            # Recursive CTE query to traverse the graph
            sql = text("""
                WITH RECURSIVE graph_traversal AS (
                    -- Anchor: root node
                    SELECT 
                        n.id, n.type, n.properties,
                        e.source, e.target, e.type as edge_type, e.properties as edge_props,
                        0 as depth
                    FROM nodes n
                    LEFT JOIN edges e ON n.id = e.source
                    WHERE n.id = :root_id
                    
                    UNION ALL
                    
                    -- Recursive: traverse edges
                    SELECT 
                        n.id, n.type, n.properties,
                        e.source, e.target, e.type, e.properties,
                        t.depth + 1
                    FROM graph_traversal t
                    JOIN edges e ON t.target = e.source
                    JOIN nodes n ON e.target = n.id
                    WHERE t.depth < :max_depth
                )
                SELECT DISTINCT * FROM graph_traversal
            """)
            
            result = session.execute(sql, {'root_id': root_node_id, 'max_depth': max_depth})
            
            # Build graph from results
            graph = Graph()
            added_nodes = set()
            
            for row in result.mappings():
                # Add node if not already added
                if row['id'] and row['id'] not in added_nodes:
                    node_dict = {
                        'id': row['id'],
                        'type': row['type'],
                        'properties': row['properties']
                    }
                    node = Node.from_dict(node_dict)
                    graph.add_node(node)
                    added_nodes.add(row['id'])
                
                # Add edge if both nodes exist
                if (row['source'] and row['target'] and 
                    row['source'] in added_nodes and row['target'] in added_nodes):
                    edge_dict = {
                        'source': row['source'],
                        'target': row['target'],
                        'type': row['edge_type'],
                        'properties': row['edge_props'] or {}
                    }
                    edge = Edge.from_dict(edge_dict)
                    graph.add_edge(edge)
            
            if len(graph.nodes) == 0:
                raise NodeNotFoundError(f"Root node not found: {root_node_id}")
            
            logger.info(f"Loaded graph from PostgreSQL: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
            return graph
            
        except SQLAlchemyError as e:
            raise StorageException(f"Failed to load graph from PostgreSQL: {e}")
        finally:
            if close_session:
                session.close()
    
    def query_nodes(self, node_type: str, filters: Dict[str, Any], 
                   limit: int = 100, offset: int = 0) -> List[Node]:
        """Query nodes by type and filters."""
        session = self._get_session()
        close_session = self._transaction_session is None
        
        try:
            query = session.query(NodeTable).filter(NodeTable.type == node_type)
            
            # Apply JSONB filters
            for key, value in filters.items():
                if key in ('limit', 'offset'):
                    continue
                
                if isinstance(value, dict):
                    # Range queries
                    for op, op_value in value.items():
                        if op == '$gt':
                            query = query.filter(
                                func.cast(NodeTable.properties[key], Integer) > op_value
                            )
                        elif op == '$gte':
                            query = query.filter(
                                func.cast(NodeTable.properties[key], Integer) >= op_value
                            )
                        elif op == '$lt':
                            query = query.filter(
                                func.cast(NodeTable.properties[key], Integer) < op_value
                            )
                        elif op == '$lte':
                            query = query.filter(
                                func.cast(NodeTable.properties[key], Integer) <= op_value
                            )
                        elif op == '$ne':
                            query = query.filter(NodeTable.properties[key] != str(op_value))
                else:
                    # Exact match
                    query = query.filter(NodeTable.properties[key] == str(value))
            
            # Apply pagination
            query = query.offset(offset).limit(limit)
            
            # Execute query and convert to Node objects
            results = []
            for row in query.all():
                node_dict = {
                    'id': row.id,
                    'type': row.type,
                    'properties': row.properties
                }
                node = Node.from_dict(node_dict)
                results.append(node)
            
            return results
            
        except SQLAlchemyError as e:
            raise StorageException(f"Failed to query nodes from PostgreSQL: {e}")
        finally:
            if close_session:
                session.close()
    
    def save_node(self, node: Node) -> None:
        """Save a single node."""
        session = self._get_session()
        close_session = self._transaction_session is None
        
        try:
            # Use merge for upsert behavior
            node_row = NodeTable(
                id=node.id,
                type=node.type,
                properties=node.properties
            )
            session.merge(node_row)
            
            if close_session:
                session.commit()
                
        except SQLAlchemyError as e:
            if close_session:
                session.rollback()
            raise StorageException(f"Failed to save node to PostgreSQL: {e}")
        finally:
            if close_session:
                session.close()
    
    def save_edge(self, edge: Edge) -> None:
        """Save a single edge."""
        session = self._get_session()
        close_session = self._transaction_session is None
        
        try:
            # Check if edge already exists
            existing = session.query(EdgeTable).filter(
                and_(
                    EdgeTable.source == edge.source,
                    EdgeTable.target == edge.target,
                    EdgeTable.type == edge.type
                )
            ).first()
            
            if not existing:
                edge_row = EdgeTable(
                    source=edge.source,
                    target=edge.target,
                    type=edge.type,
                    properties=edge.properties
                )
                session.add(edge_row)
            
            if close_session:
                session.commit()
                
        except SQLAlchemyError as e:
            if close_session:
                session.rollback()
            raise StorageException(f"Failed to save edge to PostgreSQL: {e}")
        finally:
            if close_session:
                session.close()
    
    def delete_node(self, node_id: str) -> None:
        """Delete a node and all its edges."""
        session = self._get_session()
        close_session = self._transaction_session is None
        
        try:
            # Delete all edges connected to this node
            session.query(EdgeTable).filter(
                or_(EdgeTable.source == node_id, EdgeTable.target == node_id)
            ).delete()
            
            # Delete the node
            session.query(NodeTable).filter(NodeTable.id == node_id).delete()
            
            if close_session:
                session.commit()
                
        except SQLAlchemyError as e:
            if close_session:
                session.rollback()
            raise StorageException(f"Failed to delete node from PostgreSQL: {e}")
        finally:
            if close_session:
                session.close()
    
    def delete_edge(self, source: str, target: str, edge_type: Optional[str] = None) -> None:
        """Delete edge(s) between two nodes."""
        session = self._get_session()
        close_session = self._transaction_session is None
        
        try:
            query = session.query(EdgeTable).filter(
                and_(EdgeTable.source == source, EdgeTable.target == target)
            )
            
            if edge_type:
                query = query.filter(EdgeTable.type == edge_type)
            
            query.delete()
            
            if close_session:
                session.commit()
                
        except SQLAlchemyError as e:
            if close_session:
                session.rollback()
            raise StorageException(f"Failed to delete edge from PostgreSQL: {e}")
        finally:
            if close_session:
                session.close()
    
    def get_node(self, node_id: str) -> Node:
        """Get a single node by ID."""
        session = self._get_session()
        close_session = self._transaction_session is None
        
        try:
            row = session.query(NodeTable).filter(NodeTable.id == node_id).first()
            
            if not row:
                raise NodeNotFoundError(f"Node not found: {node_id}")
            
            node_dict = {
                'id': row.id,
                'type': row.type,
                'properties': row.properties
            }
            return Node.from_dict(node_dict)
            
        except SQLAlchemyError as e:
            raise StorageException(f"Failed to get node from PostgreSQL: {e}")
        finally:
            if close_session:
                session.close()
    
    def get_edges(self, source: str, target: Optional[str] = None, 
                 edge_type: Optional[str] = None) -> List[Edge]:
        """Get edges from a source node."""
        session = self._get_session()
        close_session = self._transaction_session is None
        
        try:
            query = session.query(EdgeTable).filter(EdgeTable.source == source)
            
            if target:
                query = query.filter(EdgeTable.target == target)
            if edge_type:
                query = query.filter(EdgeTable.type == edge_type)
            
            edges = []
            for row in query.all():
                edge_dict = {
                    'source': row.source,
                    'target': row.target,
                    'type': row.type,
                    'properties': row.properties
                }
                edge = Edge.from_dict(edge_dict)
                edges.append(edge)
            
            return edges
            
        except SQLAlchemyError as e:
            raise StorageException(f"Failed to get edges from PostgreSQL: {e}")
        finally:
            if close_session:
                session.close()
    
    def node_exists(self, node_id: str) -> bool:
        """Check if a node exists."""
        session = self._get_session()
        close_session = self._transaction_session is None
        
        try:
            count = session.query(NodeTable).filter(NodeTable.id == node_id).count()
            return count > 0
        except SQLAlchemyError as e:
            raise StorageException(f"Failed to check node existence in PostgreSQL: {e}")
        finally:
            if close_session:
                session.close()
    
    def get_node_count(self, node_type: Optional[str] = None) -> int:
        """Get count of nodes."""
        session = self._get_session()
        close_session = self._transaction_session is None
        
        try:
            query = session.query(NodeTable)
            if node_type:
                query = query.filter(NodeTable.type == node_type)
            return query.count()
        except SQLAlchemyError as e:
            raise StorageException(f"Failed to get node count from PostgreSQL: {e}")
        finally:
            if close_session:
                session.close()
    
    def get_edge_count(self, edge_type: Optional[str] = None) -> int:
        """Get count of edges."""
        session = self._get_session()
        close_session = self._transaction_session is None
        
        try:
            query = session.query(EdgeTable)
            if edge_type:
                query = query.filter(EdgeTable.type == edge_type)
            return query.count()
        except SQLAlchemyError as e:
            raise StorageException(f"Failed to get edge count from PostgreSQL: {e}")
        finally:
            if close_session:
                session.close()
    
    @contextmanager
    def transaction(self):
        """Create a database transaction."""
        if self._transaction_session:
            # Nested transaction - just yield
            yield
        else:
            session = self.session_factory()
            self._transaction_session = session
            try:
                yield
                session.commit()
            except Exception as e:
                session.rollback()
                raise StorageException(f"Transaction failed: {e}")
            finally:
                session.close()
                self._transaction_session = None
    
    def clear_all(self) -> None:
        """Clear all graph data from PostgreSQL."""
        session = self._get_session()
        close_session = self._transaction_session is None
        
        try:
            session.query(EdgeTable).delete()
            session.query(NodeTable).delete()
            
            if close_session:
                session.commit()
            
            logger.info("Cleared all graph data from PostgreSQL")
        except SQLAlchemyError as e:
            if close_session:
                session.rollback()
            raise StorageException(f"Failed to clear PostgreSQL data: {e}")
        finally:
            if close_session:
                session.close()