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
from codesage.analyzers.shell_parser import ShellParser

class ShellSemanticSnapshotBuilder(BaseLanguageSnapshotBuilder):
    def build(self) -> ProjectSnapshot:
        files = self._collect_files()
        file_snapshots: List[FileSnapshot] = [self._build_file_snapshot(path) for path in files]

        dep_graph = DependencyGraph()

        for fs in file_snapshots:
            if fs.symbols and "imports" in fs.symbols:
                for imp in fs.symbols["imports"]:
                    # In shell, imports are sourced files.
                    # If they are relative, they might be internal.
                    if imp.startswith("/") or imp.startswith("http"):
                        dep_graph.external.append(imp)
                    else:
                        # Attempt to resolve? For now just list as internal edge if we can match it?
                        # Or just add to edges?
                        # dep_graph.internal.append({"source": fs.path, "target": imp})
                        pass

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
            languages=["shell"],
            language_stats={"shell": {"files": len(file_snapshots)}},
        )

    def _collect_files(self) -> List[Path]:
        files = list(self.root_path.rglob("*.sh"))
        for p in self.root_path.rglob("*"):
            if p.is_file() and p.suffix == "" and p not in files:
                try:
                    with open(p, "r") as f:
                        first_line = f.readline()
                        if first_line.startswith("#!/bin/bash") or first_line.startswith("#!/usr/bin/env bash") or first_line.startswith("#!/bin/sh"):
                            files.append(p)
                except Exception:
                    pass
        return files

    def _build_file_snapshot(self, file_path: Path) -> FileSnapshot:
        source_code = file_path.read_text()

        parser = ShellParser()
        parser.parse(source_code)

        functions = parser.extract_functions()
        variables = parser.extract_variables()
        external_commands = parser.extract_external_commands()
        imports = parser.extract_imports()

        funcs_data = [{
            "name": f.name,
            "start_line": f.start_line,
            "end_line": f.end_line
        } for f in functions]

        vars_data = [{
            "name": v.name,
            "value": v.value,
            "kind": v.kind
        } for v in variables]

        metrics = FileMetrics(
            lines_of_code=len(source_code.splitlines()),
            num_functions=len(functions),
            language_specific={
                "shell": {
                    "external_commands_count": len(external_commands),
                    "global_vars": len([v for v in variables if v.kind == "global"]),
                    "local_vars": len([v for v in variables if v.kind == "local"])
                }
            }
        )
        symbols = {
            "functions": funcs_data,
            "variables": vars_data,
            "external_commands": external_commands,
            "imports": [i.path for i in imports]
        }
        return FileSnapshot(
            path=str(file_path.relative_to(self.root_path)),
            language="shell",
            metrics=metrics,
            symbols=symbols,
        )
