import unittest
from codesage.llm.context_builder import ContextBuilder
from codesage.snapshot.models import ProjectSnapshot, FileSnapshot, SnapshotMetadata

class TestContextBuilder(unittest.TestCase):
    def setUp(self):
        self.builder = ContextBuilder(max_tokens=100) # Small limit for testing
        self.metadata = SnapshotMetadata(
            version="1.0", timestamp="2023-01-01T00:00:00Z", project_name="test",
            file_count=1, total_size=100, tool_version="1.0", config_hash="abc"
        )
        self.snapshot = ProjectSnapshot(metadata=self.metadata, files=[])

    def test_truncate_long_file(self):
        # Mock file snapshot
        fs = FileSnapshot(path="test.go", language="go", symbols={"functions": [{"name": "Main", "start_line": 0, "end_line": 10}]})

        # Write dummy content
        with open("test.go", "w") as f:
            f.write("func Main() {\n" + ("  line\n" * 20) + "}\n")

        # Builder with small window
        builder = ContextBuilder(max_tokens=50, reserve_tokens=10)

        # Should trigger compression
        context = builder.fit_to_window([fs], [], self.snapshot)

        self.assertIn("Main", context)
        self.assertIn("compressed", context)
        self.assertIn("...", context) # Body omitted

        import os
        os.remove("test.go")

    def test_prioritize_primary(self):
        fs1 = FileSnapshot(path="p1.go", language="go", symbols={})
        fs2 = FileSnapshot(path="ref.go", language="go", symbols={})

        with open("p1.go", "w") as f: f.write("content1")
        with open("ref.go", "w") as f: f.write("content2")

        builder = ContextBuilder(max_tokens=1000)
        context = builder.fit_to_window([fs1], [fs2], self.snapshot)

        self.assertIn("p1.go", context)
        self.assertIn("ref.go", context)
        self.assertIn("content1", context) # Primary full content
        self.assertIn("File: ref.go", context) # Reference summary

        import os
        os.remove("p1.go")
        os.remove("ref.go")
