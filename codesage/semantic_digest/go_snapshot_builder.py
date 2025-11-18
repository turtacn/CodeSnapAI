from __future__ import annotations
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from codesage.semantic_digest.base_builder import BaseLanguageSnapshotBuilder, SnapshotConfig
from codesage.snapshot.models import (
    ProjectSnapshot,
    FileSnapshot,
    FileMetrics,
    SnapshotMetadata,
    DependencyGraph,
)

class GoSemanticSnapshotBuilder(BaseLanguageSnapshotBuilder):
    def build(self) -> ProjectSnapshot:
        files = self._collect_files()
        file_snapshots: List[FileSnapshot] = [self._build_file_snapshot(path) for path in files]

        dep_graph = DependencyGraph()  # Simplified for now

        metadata = SnapshotMetadata(
            version="1.1",
            timestamp=datetime.now(timezone.utc),
            project_name=self.root_path.name,
            file_count=len(file_snapshots),
            total_size=sum(p.stat().st_size for p in files),
            tool_version="0.2.0",
            config_hash="dummy_hash_v2",
        )

        return ProjectSnapshot(
            metadata=metadata,
            files=file_snapshots,
            dependencies=dep_graph,
            languages=["go"],
            language_stats={"go": {"files": len(file_snapshots)}},
        )

    def _collect_files(self) -> List[Path]:
        return list(self.root_path.rglob("*.go"))

    def _build_file_snapshot(self, file_path: Path) -> FileSnapshot:
        source_code = file_path.read_text()
        lines = source_code.splitlines()

        loc = len([line for line in lines if line.strip() and not line.strip().startswith("//")])
        num_functions = len(re.findall(r"^\s*func\s+", source_code, re.MULTILINE))
        num_types = len(re.findall(r"^\s*type\s+", source_code, re.MULTILINE))

        imports = []
        in_import_block = False
        for line in lines:
            if "import (" in line:
                in_import_block = True
                continue
            if in_import_block and ")" in line:
                in_import_block = False
                continue
            if in_import_block:
                match = re.search(r'"(.+?)"', line)
                if match:
                    imports.append(match.group(1))

        metrics = FileMetrics(
            lines_of_code=loc,
            num_functions=num_functions,
            num_types=num_types,
        )
        symbols = {"imports": imports}
        return FileSnapshot(
            path=str(file_path.relative_to(self.root_path)),
            language="go",
            metrics=metrics,
            symbols=symbols,
        )
