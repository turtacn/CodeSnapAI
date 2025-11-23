from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, JSON
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    snapshots = relationship("Snapshot", back_populates="project", cascade="all, delete-orphan")

class Snapshot(Base):
    __tablename__ = 'snapshots'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=func.now())
    commit_hash = Column(String(40))
    branch = Column(String(255))
    risk_score = Column(Integer, default=0)

    # Store raw metrics as JSON if structure varies or for flexibility
    metrics = Column(JSON, nullable=True)

    project = relationship("Project", back_populates="snapshots")
    issues = relationship("Issue", back_populates="snapshot", cascade="all, delete-orphan")
    dependencies = relationship("Dependency", back_populates="snapshot", cascade="all, delete-orphan")

class Issue(Base):
    __tablename__ = 'issues'

    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, ForeignKey('snapshots.id'), nullable=False)
    file_path = Column(String(512), nullable=False)
    line_number = Column(Integer)
    severity = Column(String(20)) # LOW, MEDIUM, HIGH, ERROR
    rule_id = Column(String(100))
    description = Column(Text)

    snapshot = relationship("Snapshot", back_populates="issues")

class Dependency(Base):
    __tablename__ = 'dependencies'

    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, ForeignKey('snapshots.id'), nullable=False)
    source_file = Column(String(512))
    target_file = Column(String(512))
    type = Column(String(50)) # import, call, inheritance

    snapshot = relationship("Snapshot", back_populates="dependencies")
