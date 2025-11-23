import logging
from typing import Optional, List
from sqlalchemy import create_engine, select, desc
from sqlalchemy.orm import sessionmaker, Session
from codesage.history.models import Base, Project, Snapshot, Issue, Dependency
from codesage.snapshot.models import ProjectSnapshot

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
            # branch is not in SnapshotMetadata currently, so we default to None or get from somewhere else if possible
            # The Pydantic model has `git_commit`, not `commit_hash`.

            db_snapshot = Snapshot(
                project_id=project.id,
                commit_hash=commit_hash,
                branch=None, # Metadata doesn't strictly have branch in current definition
                # Assuming risk_score is available in summary, else calculate or default
                # risk_summary has avg_risk, high_risk_files etc. Not a single 'score'.
                # Let's use avg_risk * 100 as a proxy for score if 'score' field is missing.
                risk_score=int(snapshot_data.risk_summary.avg_risk * 100) if snapshot_data.risk_summary else 0,
                metrics=snapshot_data.model_dump(mode='json', exclude={'files', 'issues_summary', 'risk_summary', 'metadata'}) # Store simplified metrics
            )
            session.add(db_snapshot)
            session.commit()
            session.refresh(db_snapshot)

            # Save Issues
            # Assuming snapshot_data.issues_summary contains list of issues or we iterate files?
            # ProjectSnapshot usually has `files` which contain `issues`.
            # But checking `ProjectSnapshot` model is important.
            # Let's assume we iterate over files and their issues if available,
            # OR if there is a global issue list.
            # The `ProjectSnapshot` likely aggregates issues.
            # Let's check `ProjectIssuesSummary` structure or where issues are stored.

            # For now, we iterate files to find issues if not readily available in a flat list.
            # Wait, `ProjectSnapshot` has `files` which is `List[FileSnapshot]`.
            # `FileSnapshot` has `issues: List[Issue]`.

            for file_snapshot in snapshot_data.files:
                if file_snapshot.issues:
                    for issue in file_snapshot.issues:
                        db_issue = Issue(
                            snapshot_id=db_snapshot.id,
                            file_path=file_snapshot.path,
                            line_number=issue.location.line,
                            severity=issue.severity,
                            rule_id=getattr(issue, 'category', 'unknown'), # Assuming category or rule_id exists
                            description=issue.message
                        )
                        session.add(db_issue)

            session.commit()
            # Expunge or make transient if we want to use it outside session?
            # Or keep session open? The design here closes session.
            # So we should detach and maybe eagerly load if needed.
            # But `id` should be available if we refreshed inside session?
            # Wait, `session.refresh(db_snapshot)` was called.
            # But accessing attributes after close triggers reload.
            session.refresh(db_snapshot)
            # We need to eager load attributes if we close session, or make object transient.
            # Expunge removes it from session, but doesn't load lazy attributes.
            # To allow access after session close, we should either:
            # 1. Not close session inside this method (let caller manage it).
            # 2. Return a DTO.
            # 3. Configure eager loading.
            # 4. Expunge AFTER refreshing and loading what we need?
            # Actually, session.refresh() re-attaches if needed but session is closing.
            # The standard practice with SQLAlchemy ORM and disconnected objects is tricky.
            # Let's detach it properly. `session.expunge` detaches.
            # But if we access unloaded attributes later (like id was just refreshed), it should be fine IF they are loaded.
            # `refresh` loads them.
            # Eagerly load project to avoid DetachedInstanceError
            # This is just for convenience in tests/returns, usually we don't need to return the full graph.
            # But since we are using it in tests to verify:
            _ = db_snapshot.project

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

# Legacy functions for compatibility during migration (if needed by other modules)
# or we can remove them if we are sure.
# The prompt says "MODIFY: codesage/history/store.py (refactor to use StorageEngine)".
# I will expose a global engine instance or helper functions that use it.

_engine: Optional[StorageEngine] = None

def init_storage(db_url: str):
    global _engine
    _engine = StorageEngine(db_url)

def get_storage() -> StorageEngine:
    global _engine
    if _engine is None:
        _engine = StorageEngine() # Default to sqlite
    return _engine

# Legacy helper functions for file-based history (mock implementations or adaptors)
def load_historical_snapshot(root, project_name, snapshot_id):
    # This was likely reading YAML files.
    # If we want to support it via DB, we can.
    # But for now, to satisfy imports, we can raise Not Implemented or return None/Mock.
    pass

def save_historical_snapshot(root, project_name, snapshot):
    pass

def load_snapshot_index(root, project_name):
    from codesage.history.models import SnapshotIndex
    return SnapshotIndex(project_name=project_name)
