import enum
from datetime import datetime

from pgvector.sqlalchemy import Vector
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
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class PRStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    reviewed = "reviewed"
    failed = "failed"


class ReviewVerdict(str, enum.Enum):
    approve = "approve"
    request_changes = "request_changes"
    comment = "comment"


class Repository(Base):
    __tablename__ = "core_repository"

    id = Column(Integer, primary_key=True)
    owner = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    full_name = Column(String(512), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    webhook_secret = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    status = Column(SAEnum(PRStatus), default=PRStatus.pending)
    celery_task_id = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    overall_verdict = Column(SAEnum(ReviewVerdict), default=ReviewVerdict.comment)
    raw_llm_response = Column(Text, default="")
    tokens_used = Column(Integer, default=0)
    model_used = Column(String(100), default="gpt-4o-mini")
    posted_to_github = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    pull_request = relationship("PullRequest", back_populates="review")
    embedding = relationship("ReviewEmbedding", back_populates="review", uselist=False)


class ReviewEmbedding(Base):
    __tablename__ = "core_reviewembedding"

    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("core_review.id"), unique=True, nullable=False)
    # 1536 dimensions = OpenAI text-embedding-3-small
    embedding = Column(Vector(1536), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    review = relationship("Review", back_populates="embedding")
