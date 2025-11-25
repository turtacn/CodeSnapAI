import unittest
from unittest.mock import MagicMock
from codesage.llm.context_builder import ContextBuilder
from codesage.snapshot.models import ProjectSnapshot, FileSnapshot, SnapshotMetadata

class TestContextBuilder(unittest.TestCase):
    def setUp(self):
        self.snapshot = ProjectSnapshot(
            metadata=SnapshotMetadata(
                version="v1", timestamp="2023-01-01", project_name="test", file_count=1, total_size=100, tool_version="0.1", config_hash="abc"
            ),
            files=[],
            risk_summary=None,
            issues_summary=None
        )

    def test_truncate_long_file(self):
        # Mock file snapshot
        fs = FileSnapshot(path="test.go", language="go", symbols={"functions": [{"name": "Main", "start_line": 0, "end_line": 10}]})

        # Write dummy content
        with open("test.go", "w") as f:
            f.write("func Main() {\n" + ("  line\n" * 20) + "}\n")

        # Builder with slightly larger window to avoid incidental truncation of header
        builder = ContextBuilder(max_tokens=100, reserve_tokens=10)

        # Should trigger compression but keep Main
        context = builder.fit_to_window([fs], [], self.snapshot)

        self.assertIn("Main", context)

    def test_prioritize_primary(self):
        fs1 = FileSnapshot(path="p1.go", language="go", symbols={})
        fs2 = FileSnapshot(path="ref.go", language="go", symbols={})

        with open("p1.go", "w") as f: f.write("content1")
        with open("ref.go", "w") as f: f.write("content2")

        builder = ContextBuilder(max_tokens=1000)
        context = builder.fit_to_window([fs1], [fs2], self.snapshot)

        self.assertIn("p1.go", context)
        self.assertIn("ref.go", context)
        self.assertIn("content1", context)
        # Adjusted expectation to match "File: ..." format or verify content presence
        self.assertIn("content2", context)
        self.assertIn("File: ref.go", context)
