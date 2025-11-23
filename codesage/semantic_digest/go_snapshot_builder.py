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
from codesage.analyzers.go_parser import GoParser

class GoSemanticSnapshotBuilder(BaseLanguageSnapshotBuilder):
    def build(self) -> ProjectSnapshot:
        files = self._collect_files()
        file_snapshots: List[FileSnapshot] = [self._build_file_snapshot(path) for path in files]

        dep_graph = DependencyGraph()
        # Aggregate dependencies from file snapshots
        internal_pkgs = set()
        # Assume internal packages start with project name or are relative
        # Or simpler: internal dependencies are those that match other files' package?
        # Go imports are full paths.

        # We can map file path to package name if parser extracted package name.
        # GoParser currently doesn't expose package name directly, let's fix that or infer.
        # Actually GoParser should extract package name.

        for fs in file_snapshots:
            if fs.symbols and "imports" in fs.symbols:
                 for imp in fs.symbols["imports"]:
                     if "." in imp and not imp.startswith("std/"): # Heuristic
                         dep_graph.external.append(imp)

        # Deduplicate
        dep_graph.external = sorted(list(set(dep_graph.external)))

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

        parser = GoParser()
        parser.parse(source_code)

        functions = parser.extract_functions()
        structs = parser.extract_structs()
        interfaces = parser.extract_interfaces()
        imports = parser.extract_imports()
        stats = parser.get_stats()

        funcs_data = []
        for f in functions:
            d = {
                "name": f.name,
                "params": f.params,
                "return_type": f.return_type,
                "complexity": f.complexity,
                "start_line": f.start_line,
                "end_line": f.end_line
            }
            if f.receiver:
                d["receiver"] = f.receiver
            if f.decorators:
                d["decorators"] = f.decorators
            funcs_data.append(d)

        structs_data = []
        for s in structs:
            fields = []
            for f in s.fields:
                fields.append({
                    "name": f.name,
                    "type": f.type_name,
                    "kind": f.kind
                })
            structs_data.append({
                "name": s.name,
                "fields": fields
            })

        interfaces_data = []
        for i in interfaces:
            methods = []
            for m in i.methods:
                methods.append({
                    "name": m.name,
                    "params": m.params,
                    "return_type": m.return_type
                })
            interfaces_data.append({
                "name": i.name,
                "methods": methods
            })

        imports_data = [i.path for i in imports]

        metrics = FileMetrics(
            lines_of_code=len(source_code.splitlines()),
            num_functions=len(functions),
            num_types=len(structs) + len(interfaces),
            language_specific={
                "go": {
                    "goroutines": stats["goroutines"],
                    "channels": stats["channels"],
                    "error_checks": stats["errors"]
                }
            }
        )

        symbols = {
            "functions": funcs_data,
            "structs": structs_data,
            "interfaces": interfaces_data,
            "imports": imports_data
        }

        return FileSnapshot(
            path=str(file_path.relative_to(self.root_path)),
            language="go",
            metrics=metrics,
            symbols=symbols,
        )
