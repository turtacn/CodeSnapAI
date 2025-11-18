from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from codesage.snapshot.models import ProjectSnapshot, FileSnapshot

class SnapshotConfig(dict):
    pass

class BaseLanguageSnapshotBuilder(ABC):
    def __init__(self, root_path: Path, config: SnapshotConfig) -> None:
        self.root_path = root_path
        self.config = config

    @abstractmethod
    def build(self) -> ProjectSnapshot:
        ...

    @abstractmethod
    def _collect_files(self) -> List[Path]:
        ...

    @abstractmethod
    def _build_file_snapshot(self, file_path: Path) -> FileSnapshot:
        ...
