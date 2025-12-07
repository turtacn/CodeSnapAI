"""
Unit tests for IncrementalUpdater.
"""

import pytest
import tempfile
import os
import time
import threading
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from codesage.graph.incremental.updater import (
    IncrementalUpdater, ChangeType, FileChangeEvent, GraphFileHandler
)
from codesage.graph.storage.adapter import StorageAdapter, NodeNotFoundError
from codesage.graph.graph_builder import GraphBuilder
from codesage.graph.models.graph import Graph, GraphDelta
from codesage.graph.models.node import FunctionNode, FileNode


class TestFileChangeEvent:
    """Test FileChangeEvent class."""
    
    def test_creation(self):
        """Test FileChangeEvent creation."""
        event = FileChangeEvent("/path/to/file.py", ChangeType.MODIFY)
        
        assert event.file_path == "/path/to/file.py"
        assert event.change_type == ChangeType.MODIFY
        assert event.timestamp > 0
    
    def test_string_representation(self):
        """Test string representation."""
        event = FileChangeEvent("/path/to/file.py", ChangeType.CREATE)
        str_repr = str(event)
        
        assert "FileChangeEvent" in str_repr
        assert "/path/to/file.py" in str_repr
        assert "create" in str_repr


class TestGraphFileHandler:
    """Test GraphFileHandler class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_updater = Mock()
        self.watched_extensions = {'.py', '.go', '.java'}
        self.handler = GraphFileHandler(self.mock_updater, self.watched_extensions)
    
    def test_should_process_file(self):
        """Test file filtering logic."""
        # Should process Python files
        assert self.handler._should_process_file("/path/to/file.py")
        assert self.handler._should_process_file("/path/to/file.go")
        assert self.handler._should_process_file("/path/to/file.java")
        
        # Should not process other extensions
        assert not self.handler._should_process_file("/path/to/file.txt")
        assert not self.handler._should_process_file("/path/to/file.md")
        
        # Should not process hidden files
        assert not self.handler._should_process_file("/path/to/.hidden.py")
        assert not self.handler._should_process_file("/path/.hidden/file.py")
        
        # Should not process build directories
        assert not self.handler._should_process_file("/path/node_modules/file.py")
        assert not self.handler._should_process_file("/path/__pycache__/file.py")
        assert not self.handler._should_process_file("/path/.git/file.py")
    
    def test_on_created(self):
        """Test file creation event handling."""
        # Mock event
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = "/path/to/file.py"
        
        self.handler.on_created(mock_event)
        
        self.mock_updater.on_file_changed.assert_called_once_with(
            "/path/to/file.py", ChangeType.CREATE
        )
    
    def test_on_modified(self):
        """Test file modification event handling."""
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = "/path/to/file.py"
        
        self.handler.on_modified(mock_event)
        
        self.mock_updater.on_file_changed.assert_called_once_with(
            "/path/to/file.py", ChangeType.MODIFY
        )
    
    def test_on_deleted(self):
        """Test file deletion event handling."""
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = "/path/to/file.py"
        
        self.handler.on_deleted(mock_event)
        
        self.mock_updater.on_file_changed.assert_called_once_with(
            "/path/to/file.py", ChangeType.DELETE
        )
    
    def test_ignore_directory_events(self):
        """Test that directory events are ignored."""
        mock_event = Mock()
        mock_event.is_directory = True
        mock_event.src_path = "/path/to/directory"
        
        self.handler.on_created(mock_event)
        self.handler.on_modified(mock_event)
        self.handler.on_deleted(mock_event)
        
        self.mock_updater.on_file_changed.assert_not_called()


class TestIncrementalUpdater:
    """Test IncrementalUpdater class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_storage = Mock(spec=StorageAdapter)
        self.mock_builder = Mock(spec=GraphBuilder)
        self.updater = IncrementalUpdater(
            storage=self.mock_storage,
            builder=self.mock_builder,
            debounce_interval=0.1  # Short interval for testing
        )
    
    def test_initialization(self):
        """Test IncrementalUpdater initialization."""
        assert self.updater.storage == self.mock_storage
        assert self.updater.builder == self.mock_builder
        assert self.updater.debounce_interval == 0.1
        assert not self.updater._running
        assert self.updater.observer is None
    
    def test_on_file_changed_debouncing(self):
        """Test file change debouncing."""
        file_path = "/test/file.py"
        
        # First change
        self.updater.on_file_changed(file_path, ChangeType.MODIFY)
        assert self.updater.change_queue.qsize() == 1
        
        # Second change within debounce interval
        self.updater.on_file_changed(file_path, ChangeType.MODIFY)
        # Should not add to queue yet due to debouncing
        assert self.updater.change_queue.qsize() == 1
        
        # Check recent changes tracking
        assert file_path in self.updater._recent_changes
    
    def test_on_file_changed_delete_precedence(self):
        """Test that DELETE changes take precedence."""
        file_path = "/test/file.py"
        
        # First a modify
        self.updater.on_file_changed(file_path, ChangeType.MODIFY)
        
        # Then a delete - should take precedence
        self.updater.on_file_changed(file_path, ChangeType.DELETE)
        
        # Check that delete is recorded
        _, change_type = self.updater._recent_changes[file_path]
        assert change_type == ChangeType.DELETE
    
    def test_detect_language(self):
        """Test language detection from file extension."""
        assert self.updater._detect_language("/path/file.py") == "python"
        assert self.updater._detect_language("/path/file.go") == "go"
        assert self.updater._detect_language("/path/file.java") == "java"
        assert self.updater._detect_language("/path/file.js") == "javascript"
        assert self.updater._detect_language("/path/file.ts") == "typescript"
        assert self.updater._detect_language("/path/file.unknown") == "unknown"
    
    def test_compute_delta_delete(self):
        """Test computing delta for file deletion."""
        file_path = "/test/file.py"
        
        # Mock existing graph
        old_graph = Graph()
        file_node = FileNode(
            id="file:/test/file.py",
            path=file_path,
            language="python",
            loc=10
        )
        func_node = FunctionNode(
            id="func:/test/file.py:test_func",
            name="test_func",
            qualified_name="test_func",
            line_start=1,
            line_end=5
        )
        old_graph.add_node(file_node)
        old_graph.add_node(func_node)
        
        self.mock_storage.load_graph.return_value = old_graph
        
        # Compute delta for deletion
        delta = self.updater._compute_delta(file_path, ChangeType.DELETE)
        
        assert delta.has_changes()
        assert len(delta.deleted_nodes) == 2  # file and function nodes
        assert file_node.id in delta.deleted_nodes
        assert func_node.id in delta.deleted_nodes
    
    def test_compute_delta_new_file(self):
        """Test computing delta for new file."""
        file_path = "/test/new_file.py"
        
        # Mock no existing graph
        self.mock_storage.load_graph.side_effect = NodeNotFoundError("Not found")
        
        # Mock new graph creation
        new_graph = Graph()
        file_node = FileNode(
            id="file:/test/new_file.py",
            path=file_path,
            language="python",
            loc=10
        )
        new_graph.add_node(file_node)
        
        with patch.object(self.updater, '_parse_and_build_graph', return_value=new_graph):
            delta = self.updater._compute_delta(file_path, ChangeType.CREATE)
        
        assert delta.has_changes()
        assert len(delta.added_nodes) == 1
        assert delta.added_nodes[0].id == file_node.id
    
    @patch('builtins.open')
    def test_parse_and_build_graph(self, mock_open):
        """Test parsing file and building graph."""
        file_path = "/test/file.py"
        source_code = "def test_func():\n    pass"
        
        # Mock file reading
        mock_open.return_value.__enter__.return_value.read.return_value = source_code
        
        # Mock parser
        mock_parser = Mock()
        
        # Mock parser methods
        mock_parser.extract_functions.return_value = [
            Mock(
                name="test_func",
                qualified_name="test_func",
                line_start=1,
                line_end=2,
                complexity=1,
                parameters=[],
                calls=[]
            )
        ]
        mock_parser.extract_imports.return_value = []
        
        # Mock builder
        mock_graph = Graph()
        self.mock_builder.from_parser_output.return_value = mock_graph
        
        # Mock the _create_parser method
        with patch.object(self.updater, '_create_parser', return_value=mock_parser) as mock_create_parser:
            result = self.updater._parse_and_build_graph(file_path)
        
        assert result == mock_graph
        mock_create_parser.assert_called_once_with("python")
        mock_parser.parse.assert_called_once_with(source_code)
        self.mock_builder.from_parser_output.assert_called_once()
    
    def test_compute_graph_diff(self):
        """Test computing differences between graphs."""
        # Create old graph
        old_graph = Graph()
        old_func = FunctionNode(
            id="func:old_func",
            name="old_func",
            qualified_name="old_func",
            line_start=1,
            line_end=5,
            complexity=1
        )
        shared_func = FunctionNode(
            id="func:shared_func",
            name="shared_func",
            qualified_name="shared_func",
            line_start=6,
            line_end=10,
            complexity=2
        )
        old_graph.add_node(old_func)
        old_graph.add_node(shared_func)
        
        # Create new graph
        new_graph = Graph()
        new_func = FunctionNode(
            id="func:new_func",
            name="new_func",
            qualified_name="new_func",
            line_start=11,
            line_end=15,
            complexity=3
        )
        modified_shared_func = FunctionNode(
            id="func:shared_func",
            name="shared_func",
            qualified_name="shared_func",
            line_start=6,
            line_end=10,
            complexity=5  # Changed complexity
        )
        new_graph.add_node(new_func)
        new_graph.add_node(modified_shared_func)
        
        # Compute diff
        delta = GraphDelta()
        self.updater._compute_graph_diff(old_graph, new_graph, delta)
        
        # Check results
        assert len(delta.deleted_nodes) == 1
        assert old_func.id in delta.deleted_nodes
        
        assert len(delta.added_nodes) == 1
        assert delta.added_nodes[0].id == new_func.id
        
        assert len(delta.updated_nodes) == 1
        assert delta.updated_nodes[0].id == shared_func.id
        assert delta.updated_nodes[0].complexity == 5
    
    def test_apply_delta(self):
        """Test applying delta to storage."""
        delta = GraphDelta()
        func_node = FunctionNode(
            id="func:test",
            name="test",
            qualified_name="test",
            line_start=1,
            line_end=5
        )
        delta.add_node(func_node)
        
        # Mock transaction context
        self.mock_storage.transaction.return_value.__enter__ = Mock()
        self.mock_storage.transaction.return_value.__exit__ = Mock(return_value=False)
        
        self.updater._apply_delta(delta)
        
        # Verify transaction was used
        self.mock_storage.transaction.assert_called_once()
    
    def test_start_stop_processing(self):
        """Test starting and stopping change processing."""
        assert not self.updater._running
        
        # Start processing
        self.updater.start_processing()
        assert self.updater._running
        assert self.updater._processor_thread is not None
        
        # Stop processing
        self.updater.stop_processing()
        assert not self.updater._running
    
    def test_get_statistics(self):
        """Test getting updater statistics."""
        stats = self.updater.get_statistics()
        
        assert 'changes_processed' in stats
        assert 'deltas_applied' in stats
        assert 'errors' in stats
        assert 'avg_processing_time_ms' in stats
        assert 'queue_size' in stats
        assert 'recent_changes' in stats
        assert 'is_running' in stats
        assert 'is_watching' in stats
        
        assert isinstance(stats['changes_processed'], int)
        assert isinstance(stats['is_running'], bool)
    
    def test_force_update(self):
        """Test forcing update of a specific file."""
        file_path = "/test/file.py"
        
        # Test existing file
        with patch('os.path.exists', return_value=True):
            self.updater.force_update(file_path)
            assert self.updater.change_queue.qsize() > 0
        
        # Test non-existing file
        with patch('os.path.exists', return_value=False):
            self.updater.force_update(file_path)
            # Should queue DELETE event
            assert self.updater.change_queue.qsize() > 0
    
    def test_extract_functions_error_handling(self):
        """Test error handling in function extraction."""
        mock_parser = Mock()
        mock_parser.extract_functions.side_effect = Exception("Parser error")
        
        result = self.updater._extract_functions(mock_parser)
        assert result == []
    
    def test_extract_classes_error_handling(self):
        """Test error handling in class extraction."""
        mock_parser = Mock()
        mock_parser.extract_classes.side_effect = Exception("Parser error")
        
        result = self.updater._extract_classes(mock_parser)
        assert result == []
    
    def test_extract_imports_error_handling(self):
        """Test error handling in import extraction."""
        mock_parser = Mock()
        mock_parser.extract_imports.side_effect = Exception("Parser error")
        
        result = self.updater._extract_imports(mock_parser)
        assert result == []
    
    def test_process_single_change_error_handling(self):
        """Test error handling in single change processing."""
        event = FileChangeEvent("/test/file.py", ChangeType.MODIFY)
        
        # Mock compute_delta to raise exception
        with patch.object(self.updater, '_compute_delta', side_effect=Exception("Test error")):
            # Should not raise, but should increment error count
            self.updater._process_single_change(event)
            # Error count should be incremented (but we can't easily test this without more setup)
    
    def test_watched_extensions_default(self):
        """Test default watched extensions."""
        updater = IncrementalUpdater(self.mock_storage, self.mock_builder)
        
        expected_extensions = {'.py', '.go', '.java', '.js', '.ts', '.jsx', '.tsx', '.c', '.cpp', '.h', '.hpp'}
        assert updater.watched_extensions == expected_extensions
    
    def test_watched_extensions_custom(self):
        """Test custom watched extensions."""
        custom_extensions = {'.py', '.rs'}
        updater = IncrementalUpdater(
            self.mock_storage, 
            self.mock_builder,
            watched_extensions=custom_extensions
        )
        
        assert updater.watched_extensions == custom_extensions


class TestIntegrationScenarios:
    """Integration test scenarios for IncrementalUpdater."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_storage = Mock(spec=StorageAdapter)
        self.mock_builder = Mock(spec=GraphBuilder)
        self.updater = IncrementalUpdater(
            storage=self.mock_storage,
            builder=self.mock_builder,
            debounce_interval=0.05  # Very short for testing
        )
    
    def test_rapid_file_changes(self):
        """Test handling rapid file changes."""
        file_path = "/test/file.py"
        
        # Simulate rapid changes
        for i in range(5):
            self.updater.on_file_changed(file_path, ChangeType.MODIFY)
            time.sleep(0.01)  # Very short delay
        
        # Should be debounced to single change
        time.sleep(0.1)  # Wait for debounce
        
        # Queue should have limited entries due to debouncing
        assert self.updater.change_queue.qsize() <= 2
    
    def test_mixed_change_types(self):
        """Test handling mixed change types."""
        file_path = "/test/file.py"
        
        # Sequence: CREATE -> MODIFY -> DELETE
        self.updater.on_file_changed(file_path, ChangeType.CREATE)
        time.sleep(0.02)
        self.updater.on_file_changed(file_path, ChangeType.MODIFY)
        time.sleep(0.02)
        self.updater.on_file_changed(file_path, ChangeType.DELETE)
        
        # DELETE should take precedence
        time.sleep(0.1)  # Wait for debounce
        
        _, final_change_type = self.updater._recent_changes[file_path]
        assert final_change_type == ChangeType.DELETE
    
    def test_concurrent_file_changes(self):
        """Test handling concurrent changes to different files."""
        files = [f"/test/file{i}.py" for i in range(10)]
        
        # Simulate concurrent changes
        threads = []
        for file_path in files:
            thread = threading.Thread(
                target=self.updater.on_file_changed,
                args=(file_path, ChangeType.MODIFY)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All changes should be queued
        assert self.updater.change_queue.qsize() == len(files)


if __name__ == "__main__":
    pytest.main([__file__])