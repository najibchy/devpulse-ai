"""Initial schema
Revision ID: 001
Revises:
Create Date: 2024-01-01
"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table("core_repository",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(512), unique=True, nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("webhook_secret", sa.String(255), default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_table("core_pullrequest",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("core_repository.id"), nullable=False),
        sa.Column("pr_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("base_branch", sa.String(255), default="main"),
        sa.Column("head_branch", sa.String(255), nullable=False),
        sa.Column("github_url", sa.String(1024), nullable=False),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("celery_task_id", sa.String(255), default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("repository_id", "pr_number"),
    )
    op.create_table("core_review",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pull_request_id", sa.Integer(), sa.ForeignKey("core_pullrequest.id"), unique=True, nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("bugs", sa.JSON(), default=list),
        sa.Column("suggestions", sa.JSON(), default=list),
        sa.Column("security_issues", sa.JSON(), default=list),
        sa.Column("complexity_score", sa.Integer(), nullable=True),
        sa.Column("overall_verdict", sa.String(20), default="comment"),
        sa.Column("raw_llm_response", sa.Text(), default=""),
        sa.Column("tokens_used", sa.Integer(), default=0),
        sa.Column("model_used", sa.String(100), default="gpt-4o-mini"),
        sa.Column("posted_to_github", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table("core_reviewembedding",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_id", sa.Integer(), sa.ForeignKey("core_review.id"), unique=True, nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

def downgrade():
    op.drop_table("core_reviewembedding")
    op.drop_table("core_review")
    op.drop_table("core_pullrequest")
    op.drop_table("core_repository")
    op.execute("DROP EXTENSION IF EXISTS vector")
