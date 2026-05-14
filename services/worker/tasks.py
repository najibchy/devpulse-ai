import logging
import os
from datetime import datetime

from celery import Task
from config import celery_app
from github import format_review_comment, get_pr_details, get_pr_diff, post_pr_comment
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from vector_store import store_review_embedding

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://devpulse:devpulse_secret@db:5432/devpulse")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_db() -> Session:
    return SessionLocal()


class BaseTaskWithDB(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        if args:
            pr_id = args[0]
            db = get_db()
            try:
                from db_models import PullRequest
                pr = db.query(PullRequest).filter_by(id=pr_id).first()
                if pr:
                    pr.status = "failed"
                    db.commit()
            finally:
                db.close()


@celery_app.task(
    name="tasks.review_pr",
    bind=True,
    base=BaseTaskWithDB,
    max_retries=3,
    default_retry_delay=30,
)
def review_pr(self, pr_id: int):
    """
    Main review task:
    1. Fetch PR details + diff from GitHub
    2. Run LangGraph review agent
    3. Save review to DB
    4. Store embedding in pgvector
    5. Post comment to GitHub
    """
    db = get_db()
    try:
        # ── 1. Load PR from DB ────────────────────────────
        from db_models import PullRequest, Repository, Review

        pr = db.query(PullRequest).filter_by(id=pr_id).first()
        if not pr:
            logger.error(f"PR {pr_id} not found in DB")
            return

        repo = db.query(Repository).filter_by(id=pr.repository_id).first()
        if not repo:
            logger.error(f"Repo not found for PR {pr_id}")
            return

        logger.info(f"Starting review for {repo.full_name}#{pr.pr_number}")
        pr.status = "processing"
        db.commit()

        # ── 2. Fetch diff + metadata from GitHub ──────────
        try:
            diff = get_pr_diff(repo.full_name, pr.pr_number)
            details = get_pr_details(repo.full_name, pr.pr_number)
        except RuntimeError as exc:
            logger.error(f"GitHub fetch failed: {exc}")
            raise self.retry(exc=exc)

        if len(diff) > 12000:
            diff = diff[:12000] + "\n\n[diff truncated]"

        # ── 3. Run LangGraph agent ────────────────────────
        from agent import run_review_agent

        review_output = run_review_agent(
            pr_title=pr.title,
            pr_description=details.get("body", ""),
            diff=diff,
            repo_full_name=repo.full_name,
            pr_number=pr.pr_number,
        )

        # ── 4. Save review to DB ──────────────────────────
        existing_review = db.query(Review).filter_by(pull_request_id=pr.id).first()
        if existing_review:
            db.delete(existing_review)
            db.commit()

        review = Review(
            pull_request_id=pr.id,
            summary=review_output.get("summary", ""),
            bugs=review_output.get("bugs", []),
            suggestions=review_output.get("suggestions", []),
            security_issues=review_output.get("security_issues", []),
            complexity_score=review_output.get("complexity_score"),
            overall_verdict=review_output.get("overall_verdict", "comment"),
            raw_llm_response=review_output.get("raw_response", ""),
            tokens_used=review_output.get("tokens_used", 0),
            model_used=review_output.get("model_used", "gpt-4o-mini"),
            posted_to_github=False,
            created_at=datetime.utcnow(),
        )
        db.add(review)
        pr.status = "reviewed"
        db.commit()
        db.refresh(review)

        logger.info(f"Review saved (id={review.id})")

        # ── 5. Store embedding in pgvector ────────────────
        store_review_embedding(
            review_id=review.id,
            review=review_output,
        )

        # ── 6. Post comment to GitHub ─────────────────────
        comment_body = format_review_comment({
            **review_output,
            "model_used": review.model_used,
        })
        posted = post_pr_comment(repo.full_name, pr.pr_number, comment_body)

        if posted:
            review.posted_to_github = True
            db.commit()

        logger.info(f"Review complete for {repo.full_name}#{pr.pr_number}")
        return {
            "pr_id": pr_id,
            "review_id": review.id,
            "verdict": review.overall_verdict,
        }

    except Exception as exc:
        logger.exception(f"Unexpected error reviewing PR {pr_id}: {exc}")
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(name="tasks.ping")
def ping():
    return "pong"
