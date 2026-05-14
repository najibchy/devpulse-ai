"""
Re-exports SQLAlchemy models for use inside the Celery worker.
Mirrors the same table definitions as services/api/db/models.py.
"""
import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class PRStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    reviewed = "reviewed"
    failed = "failed"


class Repository(Base):
    __tablename__ = "core_repository"
    id = Column(Integer, primary_key=True)
    owner = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    full_name = Column(String(512), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    webhook_secret = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    pull_requests = relationship("PullRequest", back_populates="repository")


class PullRequest(Base):
    __tablename__ = "core_pullrequest"
    id = Column(Integer, primary_key=True)
    repository_id = Column(Integer, ForeignKey("core_repository.id"), nullable=False)
    pr_number = Column(Integer, nullable=False)
    title = Column(String(512), nullable=False)
    author = Column(String(255), nullable=False)
    base_branch = Column(String(255), default="main")
    head_branch = Column(String(255), nullable=False)
    github_url = Column(String(1024), nullable=False)
    status = Column(String(20), default="pending")
    celery_task_id = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    repository = relationship("Repository", back_populates="pull_requests")
    review = relationship("Review", back_populates="pull_request", uselist=False)
    __table_args__ = (UniqueConstraint("repository_id", "pr_number"),)


class Review(Base):
    __tablename__ = "core_review"
    id = Column(Integer, primary_key=True)
    pull_request_id = Column(Integer, ForeignKey("core_pullrequest.id"), unique=True, nullable=False)
    summary = Column(Text, nullable=False)
    bugs = Column(JSON, default=list)
    suggestions = Column(JSON, default=list)
    security_issues = Column(JSON, default=list)
    complexity_score = Column(Integer, nullable=True)
    overall_verdict = Column(String(20), default="comment")
    raw_llm_response = Column(Text, default="")
    tokens_used = Column(Integer, default=0)
    model_used = Column(String(100), default="gpt-4o-mini")
    posted_to_github = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    pull_request = relationship("PullRequest", back_populates="review")
