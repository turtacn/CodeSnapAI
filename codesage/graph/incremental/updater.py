"""
Incremental graph updater for monitoring file changes and applying deltas.
"""

import os
import time
import threading
import logging
from typing import Dict, Any, Optional, Set, Tuple
from queue import Queue, Empty
from enum import Enum
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent

from ..storage.adapter import StorageAdapter, NodeNotFoundError
from ..graph_builder import GraphBuilder
from ..models.graph import Graph, GraphDelta
from ..models.node import Node, create_node_id
from ..models.edge import Edge

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of file changes."""
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"


class FileChangeEvent:
    """Represents a file change event."""
    
    def __init__(self, file_path: str, change_type: ChangeType, timestamp: float = None):
        self.file_path = file_path
        self.change_type = change_type
        self.timestamp = timestamp or time.time()
    
    def __str__(self):
        return f"FileChangeEvent({self.file_path}, {self.change_type.value})"


class GraphFileHandler(FileSystemEventHandler):
    """File system event handler for graph updates."""
    
    def __init__(self, updater: 'IncrementalUpdater', watched_extensions: Set[str]):
        self.updater = updater
        self.watched_extensions = watched_extensions
    
    def _should_process_file(self, file_path: str) -> bool:
        """Check if file should be processed."""
        path = Path(file_path)
        
        # Check extension
        if path.suffix.lower() not in self.watched_extensions:
            return False
        
        # Skip hidden files and directories
        if any(part.startswith('.') for part in path.parts):
            return False
        
        # Skip common build/cache directories
        skip_dirs = {'node_modules', '__pycache__', '.git', 'build', 'dist', 'target'}
        if any(skip_dir in path.parts for skip_dir in skip_dirs):
            return False
        
        return True
    
    def on_created(self, event):
        if not event.is_directory and self._should_process_file(event.src_path):
            self.updater.on_file_changed(event.src_path, ChangeType.CREATE)
    
    def on_modified(self, event):
        if not event.is_directory and self._should_process_file(event.src_path):
            self.updater.on_file_changed(event.src_path, ChangeType.MODIFY)
    
    def on_deleted(self, event):
        if not event.is_directory and self._should_process_file(event.src_path):
            self.updater.on_file_changed(event.src_path, ChangeType.DELETE)


class IncrementalUpdater:
    """Incremental graph updater with file watching and delta application."""
    
    def __init__(self, storage: StorageAdapter, builder: GraphBuilder, 
                 watched_extensions: Optional[Set[str]] = None,
                 debounce_interval: float = 1.0,
                 max_queue_size: int = 1000):
        """
        Initialize incremental updater.
        
        Args:
            storage: Storage adapter for graph persistence
            builder: Graph builder for converting parser output
            watched_extensions: File extensions to watch (default: .py, .go, .java, .js, .ts)
            debounce_interval: Time to wait before processing changes (seconds)
            max_queue_size: Maximum size of change queue
        """
        self.storage = storage
        self.builder = builder
        self.debounce_interval = debounce_interval
        
        # Default watched extensions
        if watched_extensions is None:
            watched_extensions = {'.py', '.go', '.java', '.js', '.ts', '.jsx', '.tsx', '.c', '.cpp', '.h', '.hpp'}
        self.watched_extensions = watched_extensions
        
        # Change processing
        self.change_queue = Queue(maxsize=max_queue_size)
        self._recent_changes: Dict[str, Tuple[float, ChangeType]] = {}
        self._lock = threading.Lock()
        self._running = False
        self._processor_thread: Optional[threading.Thread] = None
        
        # File system watching
        self.observer: Optional[Observer] = None
        self.handler: Optional[GraphFileHandler] = None
        
        # Statistics
        self.stats = {
            'changes_processed': 0,
            'deltas_applied': 0,
            'errors': 0,
            'avg_processing_time_ms': 0.0
        }
    
    def start_watching(self, watch_paths: list[str]) -> None:
        """Start watching file system for changes."""
        if self.observer:
            logger.warning("File watcher already started")
            return
        
        self.handler = GraphFileHandler(self, self.watched_extensions)
        self.observer = Observer()
        
        for path in watch_paths:
            if os.path.exists(path):
                self.observer.schedule(self.handler, path, recursive=True)
                logger.info(f"Watching path: {path}")
            else:
                logger.warning(f"Watch path does not exist: {path}")
        
        self.observer.start()
        logger.info("File system watcher started")
    
    def stop_watching(self) -> None:
        """Stop watching file system."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            self.handler = None
            logger.info("File system watcher stopped")
    
    def start_processing(self) -> None:
        """Start background processing of changes."""
        if self._running:
            logger.warning("Change processor already running")
            return
        
        self._running = True
        self._processor_thread = threading.Thread(target=self._process_changes, daemon=True)
        self._processor_thread.start()
        logger.info("Change processor started")
    
    def stop_processing(self) -> None:
        """Stop background processing of changes."""
        self._running = False
        if self._processor_thread:
            self._processor_thread.join(timeout=5.0)
            self._processor_thread = None
        logger.info("Change processor stopped")
    
    def on_file_changed(self, file_path: str, change_type: ChangeType) -> None:
        """Handle file change event with deduplication."""
        current_time = time.time()
        
        with self._lock:
            # Check for recent changes (debouncing)
            if file_path in self._recent_changes:
                last_time, last_type = self._recent_changes[file_path]
                if current_time - last_time < self.debounce_interval:
                    # Merge change types: DELETE takes precedence
                    if change_type == ChangeType.DELETE or last_type == ChangeType.DELETE:
                        change_type = ChangeType.DELETE
                    else:
                        change_type = ChangeType.MODIFY
                    
                    # Update timestamp but don't queue yet
                    self._recent_changes[file_path] = (current_time, change_type)
                    return
            
            # Record this change
            self._recent_changes[file_path] = (current_time, change_type)
        
        # Queue the change for processing
        try:
            event = FileChangeEvent(file_path, change_type, current_time)
            self.change_queue.put_nowait(event)
            logger.debug(f"Queued change: {event}")
        except Exception as e:
            logger.error(f"Failed to queue change for {file_path}: {e}")
            self.stats['errors'] += 1
    
    def _process_changes(self) -> None:
        """Background thread for processing file changes."""
        logger.info("Change processing thread started")
        
        while self._running:
            try:
                # Wait for changes with timeout
                try:
                    event = self.change_queue.get(timeout=1.0)
                except Empty:
                    continue
                
                # Check if this change is still recent (debouncing)
                with self._lock:
                    if event.file_path in self._recent_changes:
                        last_time, last_type = self._recent_changes[event.file_path]
                        if time.time() - last_time < self.debounce_interval:
                            # Put it back and wait
                            self.change_queue.put_nowait(event)
                            time.sleep(0.1)
                            continue
                        
                        # Remove from recent changes
                        del self._recent_changes[event.file_path]
                
                # Process the change
                start_time = time.time()
                try:
                    self._process_single_change(event)
                    self.stats['changes_processed'] += 1
                except Exception as e:
                    logger.error(f"Error processing change {event}: {e}")
                    self.stats['errors'] += 1
                
                # Update timing statistics
                processing_time = (time.time() - start_time) * 1000
                self.stats['avg_processing_time_ms'] = (
                    (self.stats['avg_processing_time_ms'] * (self.stats['changes_processed'] - 1) + processing_time) /
                    self.stats['changes_processed']
                )
                
                logger.debug(f"Processed {event} in {processing_time:.2f}ms")
                
            except Exception as e:
                logger.error(f"Unexpected error in change processing: {e}")
                self.stats['errors'] += 1
        
        logger.info("Change processing thread stopped")
    
    def _process_single_change(self, event: FileChangeEvent) -> None:
        """Process a single file change event."""
        try:
            # Compute delta
            delta = self._compute_delta(event.file_path, event.change_type)
            
            if delta.has_changes():
                # Apply delta
                self._apply_delta(delta)
                self.stats['deltas_applied'] += 1
                
                logger.info(f"Applied delta for {event.file_path}: {delta}")
            else:
                logger.debug(f"No changes detected for {event.file_path}")
                
        except Exception as e:
            logger.error(f"Failed to process change for {event.file_path}: {e}")
            self.stats['errors'] += 1
    
    def _compute_delta(self, file_path: str, change_type: ChangeType) -> GraphDelta:
        """Compute graph delta for a file change."""
        delta = GraphDelta()
        
        # Load existing graph for this file
        old_graph = None
        file_id = create_node_id('file', file_path)
        
        try:
            old_graph = self.storage.load_graph(file_id, max_depth=1)
        except NodeNotFoundError:
            # File not in graph yet
            pass
        except Exception as e:
            logger.debug(f"Could not load existing graph for {file_path}: {e}")
        
        # Handle DELETE case
        if change_type == ChangeType.DELETE:
            if old_graph:
                # Mark all nodes and edges for deletion
                for node_id in old_graph.nodes:
                    delta.delete_node(node_id)
                for edge in old_graph.edges:
                    delta.delete_edge(edge.source, edge.target, edge.type)
            return delta
        
        # For CREATE/MODIFY: parse file and build new graph
        try:
            new_graph = self._parse_and_build_graph(file_path)
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return delta
        
        # Compare graphs and compute delta
        if old_graph:
            self._compute_graph_diff(old_graph, new_graph, delta)
        else:
            # New file - add all nodes and edges
            for node in new_graph.nodes.values():
                delta.add_node(node)
            for edge in new_graph.edges:
                delta.add_edge(edge)
        
        return delta
    
    def _create_parser(self, language: str):
        """Create parser for given language."""
        # Import parser factory here to avoid circular imports
        from ...analyzers.parser_factory import create_parser
        return create_parser(language)
    
    def _parse_and_build_graph(self, file_path: str) -> Graph:
        """Parse file and build graph."""
        # Detect language
        language = self._detect_language(file_path)
        
        # Create parser
        parser = self._create_parser(language)
        
        # Read and parse file
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        parser.parse(source_code)
        
        # Convert to parser output format
        parser_output = {
            'file_path': file_path,
            'language': language,
            'source_code': source_code,
            'functions': self._extract_functions(parser),
            'classes': self._extract_classes(parser),
            'imports': self._extract_imports(parser),
            'metrics': {
                'loc': len(source_code.splitlines())
            }
        }
        
        # Build graph
        return self.builder.from_parser_output(parser_output)
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext = Path(file_path).suffix.lower()
        
        language_map = {
            '.py': 'python',
            '.go': 'go',
            '.java': 'java',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp'
        }
        
        return language_map.get(ext, 'unknown')
    
    def _extract_functions(self, parser) -> list:
        """Extract functions from parser."""
        try:
            functions = parser.extract_functions()
            return [
                {
                    'name': func.name,
                    'qualified_name': func.qualified_name,
                    'line_start': func.line_start,
                    'line_end': func.line_end,
                    'complexity': func.complexity,
                    'parameters': func.parameters,
                    'calls': func.calls
                }
                for func in functions
            ]
        except Exception as e:
            logger.debug(f"Error extracting functions: {e}")
            return []
    
    def _extract_classes(self, parser) -> list:
        """Extract classes from parser."""
        try:
            # This would need to be implemented in the parser
            return []
        except Exception as e:
            logger.debug(f"Error extracting classes: {e}")
            return []
    
    def _extract_imports(self, parser) -> list:
        """Extract imports from parser."""
        try:
            imports = parser.extract_imports()
            return [
                {
                    'module': imp.module,
                    'name': imp.name,
                    'alias': imp.alias,
                    'type': 'import'
                }
                for imp in imports
            ]
        except Exception as e:
            logger.debug(f"Error extracting imports: {e}")
            return []
    
    def _compute_graph_diff(self, old_graph: Graph, new_graph: Graph, delta: GraphDelta) -> None:
        """Compute differences between old and new graphs."""
        old_node_ids = set(old_graph.nodes.keys())
        new_node_ids = set(new_graph.nodes.keys())
        
        # Deleted nodes
        for node_id in old_node_ids - new_node_ids:
            delta.delete_node(node_id)
        
        # Added nodes
        for node_id in new_node_ids - old_node_ids:
            delta.add_node(new_graph.nodes[node_id])
        
        # Modified nodes
        for node_id in old_node_ids & new_node_ids:
            old_node = old_graph.nodes[node_id]
            new_node = new_graph.nodes[node_id]
            
            if old_node.properties != new_node.properties:
                delta.update_node(new_node)
        
        # Edge differences
        old_edges = {(e.source, e.target, e.type) for e in old_graph.edges}
        new_edges = {(e.source, e.target, e.type) for e in new_graph.edges}
        
        # Deleted edges
        for edge_key in old_edges - new_edges:
            delta.delete_edge(edge_key[0], edge_key[1], edge_key[2])
        
        # Added edges
        edge_map = {(e.source, e.target, e.type): e for e in new_graph.edges}
        for edge_key in new_edges - old_edges:
            delta.add_edge(edge_map[edge_key])
    
    def _apply_delta(self, delta: GraphDelta) -> None:
        """Apply graph delta to storage."""
        try:
            with self.storage.transaction():
                delta.apply_to_storage(self.storage)
        except Exception as e:
            logger.error(f"Failed to apply delta: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get updater statistics."""
        return {
            **self.stats,
            'queue_size': self.change_queue.qsize(),
            'recent_changes': len(self._recent_changes),
            'is_running': self._running,
            'is_watching': self.observer is not None
        }
    
    def force_update(self, file_path: str) -> None:
        """Force update of a specific file."""
        if os.path.exists(file_path):
            self.on_file_changed(file_path, ChangeType.MODIFY)
        else:
            self.on_file_changed(file_path, ChangeType.DELETE)


# Extend GraphDelta to support storage operations
def apply_to_storage(self, storage: StorageAdapter) -> None:
    """Apply delta to storage adapter."""
    # Delete edges first
    for source, target, edge_type in self.deleted_edges:
        storage.delete_edge(source, target, edge_type if edge_type != '*' else None)
    
    # Delete nodes
    for node_id in self.deleted_nodes:
        storage.delete_node(node_id)
    
    # Add/update nodes
    for node in self.added_nodes + self.updated_nodes:
        storage.save_node(node)
    
    # Add edges
    for edge in self.added_edges:
        storage.save_edge(edge)

# Monkey patch the method
GraphDelta.apply_to_storage = apply_to_storage