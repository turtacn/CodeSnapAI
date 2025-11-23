from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from tree_sitter import Language, Parser, Tree
from codesage.analyzers.base import BaseParser
from codesage.analyzers.parser_factory import create_parser

class CompressionStrategy(ABC):
    """Abstract base class for code compression strategies."""

    def __init__(self):
        # We might want to inject a tokenizer here or assume one
        pass

    @abstractmethod
    def compress(self, code: str, file_path: str, language_id: str) -> str:
        """
        Compresses the given code.

        Args:
            code: The source code content.
            file_path: The path to the file (for context/logging).
            language_id: The language identifier (e.g., 'python', 'go').

        Returns:
            The compressed code string.
        """
        pass

class FullStrategy(CompressionStrategy):
    """Retains the full code."""

    def compress(self, code: str, file_path: str, language_id: str) -> str:
        return code

class SkeletonStrategy(CompressionStrategy):
    """
    Retains AST structure, imports, signatures, and docstrings.
    Replaces function bodies with '...'.
    """

    def compress(self, code: str, file_path: str, language_id: str) -> str:
        try:
            parser_instance = create_parser(language_id)
        except ValueError:
            # Fallback if parser not found for language
            return code

        # Parse the code
        # Note: BaseParser typically provides a parse method but it might return custom ASTNode.
        # We need the tree-sitter tree for precise text replacement.
        # But BaseParser wraps tree-sitter. Let's see if we can get the raw tree or use the parser directly.
        # codesage.analyzers.base.BaseParser usually has self.parser

        # Accessing the tree-sitter parser from the wrapper
        ts_parser = parser_instance.parser
        tree = ts_parser.parse(bytes(code, "utf8"))

        return self._prune_tree(code, tree, language_id)

    def _prune_tree(self, code: str, tree: Tree, language: str) -> str:
        # We need language specific queries to identify bodies
        # For Python: 'block' inside 'function_definition'
        # For Go: 'block' inside 'function_declaration' or 'method_declaration'

        root_node = tree.root_node

        # We will collect ranges to exclude
        exclude_ranges = []

        # Helper to find nodes
        # We can use tree-sitter queries.

        query_scm = ""
        if language == "python":
            query_scm = """
            (function_definition
              body: (block) @body)
            (class_definition
              body: (block
                (expression_statement) @docstring . ) @class_body)
            """
            # Note: For class, we want to keep methods but maybe hide other things?
            # Actually, typically we keep method signatures inside classes.
            # So for classes, we don't prune the whole block, we iterate inside.
            # But for functions, we prune the block.

            # Revised query for Python:
            query_scm = """
            (function_definition
              body: (block) @body)
            """
        elif language == "go":
            query_scm = """
            (function_declaration
              body: (block) @body)
            (method_declaration
              body: (block) @body)
            (func_literal
              body: (block) @body)
            """
        else:
            # Fallback for unsupported languages in skeleton strategy
            return code

        # Execute query
        try:
            language_obj = tree.language
            query = language_obj.query(query_scm)
            # captures() method was removed or changed in newer versions of tree-sitter.
            # Using QueryCursor if available, or just captures() if it's on query.
            # Modern API: query.captures(node) returns dict or list?
            # From memory instructions: "Use QueryCursor to execute queries as Query.captures is removed."
            # Actually, `query.captures` exists in some versions but might be deprecated.
            # The error said "Query object has no attribute captures".
            # So we must use QueryCursor if available, or language.query is returning a Query object.

            # Re-checking memory: "The project uses tree-sitter version >= 0.22, requiring the use of QueryCursor to execute queries as Query.captures is removed."

            from tree_sitter import QueryCursor
            cursor = QueryCursor(query)
            captures = cursor.captures(root_node)

            # We work with bytes to ensure correct slicing/replacement
            code_bytes_ref = code.encode("utf8")

            # Normalize captures to a list of (node, capture_name)
            flat_captures = []
            if isinstance(captures, dict):
                for name, nodes in captures.items():
                    for node in nodes:
                        flat_captures.append((node, name))
            elif isinstance(captures, list):
                # captures is a list of tuples (node, capture_name) in newer versions
                # Or (node, capture_index) in older versions.
                # But `cursor.captures` typically returns (Node, str) in the python binding provided by tree_sitter package >= 0.22?
                # Actually, in some versions it is (Node, str).
                # In others it might be (Node, int).
                # But since we saw "too many values to unpack", it suggests it might not be a 2-tuple.
                # However, the reviewer says "captures() returns a list of tuples (Node, str)".
                # Let's assume the reviewer is correct and handle potential variations.

                for item in captures:
                    if len(item) == 2:
                        node, name_or_idx = item
                        if isinstance(name_or_idx, int):
                            name = query.capture_names[name_or_idx]
                        else:
                            name = name_or_idx
                        flat_captures.append((node, name))
                    else:
                        # Fallback for unknown format
                        pass

            for node, name in flat_captures:
                if name == "body":
                    # Refined approach for Python:
                    # Check if the first child of the block is a string expression (docstring).
                    start_byte = node.start_byte
                    end_byte = node.end_byte

                    # Check for docstring in Python
                    if language == "python":
                        if node.child_count > 0:
                            first_child = node.children[0]
                            if first_child.type == 'expression_statement':
                                # Check if it looks like a string
                                # We might need to dig deeper or check text
                                # Use bytes slicing
                                text_bytes = code_bytes_ref[first_child.start_byte:first_child.end_byte].strip()
                                if text_bytes.startswith((b'"""', b"'''", b'"', b"'")):
                                    # It's a docstring, keep it.
                                    # We prune from after the docstring to the end of the block.
                                    start_byte = first_child.end_byte

                    exclude_ranges.append((start_byte, end_byte))

        except Exception as e:
            print(f"Error executing query for {language}: {e}")
            return code

        # Apply exclusions
        # Sort ranges by start_byte reversed to avoid index shifting
        exclude_ranges.sort(key=lambda x: x[0], reverse=True)

        # We need to be careful about nested ranges?
        # The query shouldn't return nested bodies if we are just selecting function bodies,
        # unless we have functions inside functions.
        # If we remove the outer body, the inner one is gone too.
        # Tree-sitter captures might return both.
        # If we process reversed, we remove inner then outer.
        # Actually if we remove outer, the inner removal is redundant but harmless if we work on the string or bytearray.
        # Wait, if we modify the string, indices shift.
        # So we MUST work reversed and ensure ranges don't overlap in a way that breaks things.
        # Or easier: reconstruct the string.

        # Let's use string reconstruction or bytearray modification

        # Better: Filter out ranges that are contained in other ranges to avoid double work or errors?
        # If (A, B) contains (C, D), and we process (C, D) first (higher start), we replace C..D.
        # Then we process (A, B). Since B > D and A < C, A..B now covers the modified area.
        # But indices A and B are from the ORIGINAL string.
        # If we modify the string, we must track the shift.

        # Simple algorithm:
        # 1. Collect all ranges (start, end)
        # 2. Merge overlapping/nested ranges. (If nested, just take the outer one? Yes, if outer body is removed, inner is too).
        # 3. Apply replacements from end to start.

        # Merging ranges:
        # Sort by start.
        if not exclude_ranges:
            return code

        # Re-sort for merging
        exclude_ranges.sort(key=lambda x: x[0])

        merged = []
        if exclude_ranges:
            curr_start, curr_end = exclude_ranges[0]
            for next_start, next_end in exclude_ranges[1:]:
                if next_start < curr_end:
                    # Overlap or nested
                    # If nested (next_end <= curr_end), we ignore the inner one (it's covered).
                    # If partial overlap (unlikely for tree nodes of this type), we extend?
                    # AST nodes nest. So if next starts before current ends, it must be a child (or we have weird overlap).
                    # We take the max end.
                    curr_end = max(curr_end, next_end)
                else:
                    merged.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            merged.append((curr_start, curr_end))

        # Now apply reversed
        code_bytes = bytearray(code, "utf8")

        replacement = b"\n    ... # Pruned\n"

        for start, end in reversed(merged):
             # We might want to check if the range is empty (e.g. empty block)
             if end > start:
                 # Check if we are preserving docstrings (adjusted start)
                 # If we adjusted start, we need to ensure indentation is correct for the replacement.

                 # Simple replacement
                 code_bytes[start:end] = replacement

        return code_bytes.decode("utf8")


class SignatureStrategy(CompressionStrategy):
    """
    Retains only top-level definitions (global variables, class names, function names).
    Drastic reduction.
    """

    def compress(self, code: str, file_path: str, language_id: str) -> str:
        # We can use Tree-sitter to find top-level nodes and just list them.
        # Or use a simpler approach if available.

        try:
            parser_instance = create_parser(language_id)
        except ValueError:
            return "" # Or return simplified message

        ts_parser = parser_instance.parser
        tree = ts_parser.parse(bytes(code, "utf8"))
        root = tree.root_node

        lines = []
        lines.append(f"# Signature Digest for {file_path}")

        # Iterate top-level children
        for child in root.children:
            if child.type == "function_definition":
                name = self._get_name(child, code)
                lines.append(f"def {name}(...): ...")
            elif child.type == "class_definition":
                name = self._get_name(child, code)
                lines.append(f"class {name}: ...")
            elif child.type == "function_declaration": # Go
                name = self._get_name(child, code)
                lines.append(f"func {name}(...) ...")
            # Add more types as needed

        return "\n".join(lines)

    def _get_name(self, node, code):
        # Find 'name' or 'identifier' child
        # Use bytes to handle unicode offsets correctly
        code_bytes = code.encode("utf8")
        for child in node.children:
            if child.type == "identifier" or child.type == "name":
                return code_bytes[child.start_byte:child.end_byte].decode("utf8")
        return "?"

class CompressionStrategyFactory:
    @staticmethod
    def get_strategy(level: str) -> CompressionStrategy:
        if level == "skeleton":
            return SkeletonStrategy()
        elif level == "signature":
            return SignatureStrategy()
        else:
            return FullStrategy()
