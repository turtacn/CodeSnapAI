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

class ShellSemanticSnapshotBuilder(BaseLanguageSnapshotBuilder):
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
                        if first_line.startswith("#!/bin/bash") or first_line.startswith("#!/usr/bin/env bash"):
                            files.append(p)
                except Exception:
                    pass
        return files

    def _build_file_snapshot(self, file_path: Path) -> FileSnapshot:
        source_code = file_path.read_text()
        lines = source_code.splitlines()

        loc = len([line for line in lines if line.strip() and not line.strip().startswith("#")])
        num_functions = len(re.findall(r"^\s*(?:function\s+)?\w+\s*\(\s*\)\s*\{", source_code, re.MULTILINE))

        external_commands = set()
        for line in lines:
            if line.strip() and not line.strip().startswith("#"):
                match = re.match(r"^\s*(\w+)", line)
                if match:
                    # A simple heuristic to avoid shell keywords
                    if match.group(1) not in ["if", "then", "else", "fi", "for", "do", "done", "while", "until", "case", "esac", "function"]:
                        external_commands.add(match.group(1))

        metrics = FileMetrics(
            lines_of_code=loc,
            num_functions=num_functions,
            language_specific={"shell": {"external_commands_count": len(external_commands)}},
        )
        symbols = {"external_commands": list(external_commands)}
        return FileSnapshot(
            path=str(file_path.relative_to(self.root_path)),
            language="shell",
            metrics=metrics,
            symbols=symbols,
        )
