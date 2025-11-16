import fnmatch
import json
import hashlib
from typing import Any, Dict, List

from codesage.snapshot.models import ProjectSnapshot, FileSnapshot
from codesage.analyzers.ast_models import ASTNode


class SnapshotCompressor:
    """Compresses a ProjectSnapshot to reduce its size."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config.get("compression", {})
        self.exclude_patterns = self.config.get("exclude_patterns", [])
        self.trimming_threshold = self.config.get("trimming_threshold", 1000)

    def compress(self, snapshot: ProjectSnapshot) -> ProjectSnapshot:
        """
        Compresses the snapshot by applying various techniques.
        """
        compressed_snapshot = snapshot.model_copy(deep=True)

        if self.exclude_patterns:
            compressed_snapshot.files = self._exclude_files(
                compressed_snapshot.files, self.exclude_patterns
            )

        compressed_snapshot.files = self._deduplicate_ast_nodes(compressed_snapshot.files)
        compressed_snapshot.files = self._trim_large_asts(
            compressed_snapshot.files, self.trimming_threshold
        )

        return compressed_snapshot

    def _exclude_files(
        self, files: List[FileSnapshot], patterns: List[str]
    ) -> List[FileSnapshot]:
        """Filters out files that match the exclude patterns."""
        return [
            file
            for file in files
            if not any(fnmatch.fnmatch(file.path, pattern) for pattern in patterns)
        ]

    def _deduplicate_ast_nodes(
        self, files: List[FileSnapshot]
    ) -> List[FileSnapshot]:
        """
        Deduplicates AST nodes by replacing identical subtrees with a reference.
        This is a simplified implementation. A real one would need a more robust
        hashing and reference mechanism.
        """
        node_cache = {}
        for file in files:
            if file.ast_summary: # Assuming ast_summary holds the AST
                self._traverse_and_deduplicate(file.ast_summary, node_cache)
        return files

    def _traverse_and_deduplicate(self, node: ASTNode, cache: Dict[str, ASTNode]):
        """Recursively traverses the AST and deduplicates nodes."""
        if not isinstance(node, ASTNode):
            return

        node_hash = self._hash_node(node)
        if node_hash in cache:
            # Replace with a reference to the cached node
            # This is a conceptual implementation. In practice, you might
            # store the canonical node in a separate structure and use IDs.
            node = cache[node_hash]
            return

        cache[node_hash] = node
        for i, child in enumerate(node.children):
            node.children[i] = self._traverse_and_deduplicate(child, cache)

    def _hash_node(self, node: ASTNode) -> str:
        """Creates a stable hash for an AST node."""
        # A simple hash based on type and value. A real implementation
        # should be more robust, considering children as well.
        hasher = hashlib.md5()
        hasher.update(node.node_type.encode())
        if node.value:
            hasher.update(str(node.value).encode())
        return hasher.hexdigest()

    def _trim_large_asts(
        self, files: List[FileSnapshot], threshold: int
    ) -> List[FileSnapshot]:
        """Trims the AST of very large files to save space."""
        for file in files:
            if file.lines > threshold and file.ast_summary:
                self._traverse_and_trim(file.ast_summary)
        return files

    def _traverse_and_trim(self, node: ASTNode):
        """
        Recursively traverses the AST and removes non-essential nodes,
        like the bodies of functions.
        """
        if not isinstance(node, ASTNode):
            return

        # For function nodes, keep the signature but remove the body
        if node.node_type == "function":
            node.children = [] # A simple way to trim the function body
            return

        for child in node.children:
            self._traverse_and_trim(child)


    def calculate_compression_ratio(
        self, original: ProjectSnapshot, compressed: ProjectSnapshot
    ) -> float:
        """Calculates the compression ratio."""
        original_size = len(json.dumps(original.model_dump(mode='json')))
        compressed_size = len(json.dumps(compressed.model_dump(mode='json')))
        if original_size == 0:
            return 0.0
        return (original_size - compressed_size) / original_size
