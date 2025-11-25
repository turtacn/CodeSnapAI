import logging
import os
import json
import yaml
from typing import Optional, List, Union, Any
from sqlalchemy import create_engine, select, desc
from sqlalchemy.orm import sessionmaker, Session, joinedload
from codesage.history.models import Base, Project, Snapshot, Issue, Dependency, SnapshotIndex, HistoricalSnapshot
from codesage.snapshot.models import ProjectSnapshot, SnapshotMetadata, FileSnapshot, FileMetrics, FileRisk, Issue as PydanticIssue

logger = logging.getLogger(__name__)

class StorageEngine:
    def __init__(self, db_url: str = "sqlite:///codesage.db"):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    def save_snapshot(self, project_name: str, snapshot_data: ProjectSnapshot) -> Snapshot:
        """
        Saves a ProjectSnapshot to the database.
        """
        session = self.get_session()
        try:
            # Get or create Project
            project = session.execute(select(Project).where(Project.name == project_name)).scalar_one_or_none()
            if not project:
                project = Project(name=project_name)
                session.add(project)
                session.commit()
                session.refresh(project)

            # Create Snapshot record
            meta = snapshot_data.metadata

            # Handle field differences between SnapshotMetadata and SQLAlchemy model
            commit_hash = getattr(meta, 'git_commit', None)

            db_snapshot = Snapshot(
                project_id=project.id,
                commit_hash=commit_hash,
                branch=None,
                risk_score=int(snapshot_data.risk_summary.avg_risk * 100) if snapshot_data.risk_summary else 0,
                metrics=snapshot_data.model_dump(mode='json', exclude={'files', 'issues_summary', 'risk_summary', 'metadata'}) # Store simplified metrics
            )
            session.add(db_snapshot)
            session.commit()
            session.refresh(db_snapshot)

            # Files handling
            files = snapshot_data.files

            # Normalize to list of (path, snapshot)
            file_items = []
            if isinstance(files, dict):
                for path, fsnap in files.items():
                    file_items.append((path, fsnap))
            elif isinstance(files, list):
                for fsnap in files:
                    file_items.append((getattr(fsnap, 'path', 'unknown'), fsnap))

            for path, file_snapshot in file_items:
                if hasattr(file_snapshot, 'issues') and file_snapshot.issues:
                    for issue in file_snapshot.issues:
                        line_num = getattr(issue, 'line', 0)
                        if hasattr(issue, 'location') and hasattr(issue.location, 'line'):
                            line_num = issue.location.line

                        # Use path from key if file_snapshot doesn't have it (e.g. mock)
                        issue_path = getattr(file_snapshot, 'path', path)
                        if issue_path == 'unknown': issue_path = path

                        db_issue = Issue(
                            snapshot_id=db_snapshot.id,
                            file_path=issue_path,
                            line_number=line_num,
                            severity=issue.severity,
                            rule_id=getattr(issue, 'category', getattr(issue, 'rule_id', 'unknown')),
                            description=issue.message
                        )
                        session.add(db_issue)

            session.commit()
            session.refresh(db_snapshot)
            _ = db_snapshot.project
            _ = db_snapshot.issues

            session.expunge(db_snapshot)
            return db_snapshot
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save snapshot: {e}")
            raise
        finally:
            session.close()

    def get_latest_snapshot(self, project_name: str) -> Optional[Snapshot]:
        session = self.get_session()
        try:
            project = session.execute(select(Project).where(Project.name == project_name)).scalar_one_or_none()
            if not project:
                return None

            stmt = select(Snapshot).where(Snapshot.project_id == project.id).order_by(desc(Snapshot.timestamp)).limit(1)
            return session.execute(stmt).scalar_one_or_none()
        finally:
            session.close()

    def get_history(self, project_name: str, limit: int = 10) -> List[Snapshot]:
        session = self.get_session()
        try:
            project = session.execute(select(Project).where(Project.name == project_name)).scalar_one_or_none()
            if not project:
                return []

            stmt = select(Snapshot).where(Snapshot.project_id == project.id).order_by(desc(Snapshot.timestamp)).limit(limit)
            return session.execute(stmt).scalars().all()
        finally:
            session.close()

# Legacy functions for compatibility
_engine: Optional[StorageEngine] = None

def init_storage(db_url: str):
    global _engine
    _engine = StorageEngine(db_url)

def get_storage() -> StorageEngine:
    global _engine
    if _engine is None:
        _engine = StorageEngine() # Default to sqlite
    return _engine

def load_historical_snapshot(root, project_name, snapshot_id):
    """Legacy load from file"""
    path = os.path.join(root, project_name, "snapshots", f"{snapshot_id}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
            return HistoricalSnapshot(**data)
    return None

def save_historical_snapshot(root, snapshot: Union[HistoricalSnapshot, Any], config: Optional[Any] = None):
    """
    Legacy save to file.
    """
    project_name = "unknown"

    if isinstance(snapshot, str):
        project_name = snapshot
        snapshot_obj = config
    else:
        snapshot_obj = snapshot
        if hasattr(snapshot_obj, 'meta') and snapshot_obj.meta.project_name:
            project_name = snapshot_obj.meta.project_name
        elif hasattr(snapshot_obj, 'metadata') and snapshot_obj.metadata.project_name:
            project_name = snapshot_obj.metadata.project_name

    if hasattr(snapshot_obj, 'meta'):
        snapshot_id = snapshot_obj.meta.snapshot_id
    elif hasattr(snapshot_obj, 'metadata'):
        snapshot_id = getattr(snapshot_obj.metadata, 'snapshot_id', 'latest')
    else:
        snapshot_id = 'unknown'

    path = os.path.join(root, project_name, "snapshots", f"{snapshot_id}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(snapshot_obj.model_dump_json(indent=2))

def load_snapshot_index(root, project_name):
    path = os.path.join(root, project_name, "index.yaml")
    if os.path.exists(path):
        with open(path, "r") as f:
            data = yaml.safe_load(f)
            return SnapshotIndex(**data)
    return SnapshotIndex(project_name=project_name)

def update_snapshot_index(root, new_snapshot_meta, max_snapshots=10):
    """
    Update index.
    """
    project_name = "unknown"
    meta = new_snapshot_meta

    if isinstance(new_snapshot_meta, str):
        project_name = new_snapshot_meta
        if hasattr(meta, 'project_name'):
            project_name = meta.project_name
    else:
        if hasattr(meta, 'project_name'):
            project_name = meta.project_name

    path = os.path.join(root, project_name, "index.yaml")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    index = load_snapshot_index(root, project_name)

    meta_obj = meta

    index.items.insert(0, meta_obj)
    index.items = index.items[:max_snapshots]

    with open(path, "w") as f:
        yaml.safe_dump(index.model_dump(mode='json'), f)
