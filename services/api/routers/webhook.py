import hashlib
import hmac
import logging
import os

from db.models import PullRequest, Repository
from db.session import get_db
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from schemas import PRResponse, WebhookPayload
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")


def verify_signature(payload_bytes: bytes, signature_header: str) -> bool:
    """Verify the GitHub webhook HMAC-SHA256 signature."""
    if not GITHUB_WEBHOOK_SECRET:
        logger.warning("No webhook secret set — skipping signature verification")
        return True

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        key=GITHUB_WEBHOOK_SECRET.encode(),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()

    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)


@router.post("/github", response_model=PRResponse)
async def github_webhook(
    request: Request,
    x_github_event: str = Header(...),
    x_hub_signature_256: str = Header(default=""),
    db: Session = Depends(get_db),
):
    payload_bytes = await request.body()

    # ── Signature verification ────────────────────────────
    if not verify_signature(payload_bytes, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # ── Only handle pull_request events ──────────────────
    if x_github_event != "pull_request":
        return PRResponse(message=f"Ignored event: {x_github_event}", pr_id=0, task_id="")

    # ── Parse payload ─────────────────────────────────────
    try:
        payload = WebhookPayload.model_validate_json(payload_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid payload: {e}")

    # ── Only process opened or synchronize actions ────────
    if payload.action not in ("opened", "synchronize"):
        return PRResponse(message=f"Ignored action: {payload.action}", pr_id=0, task_id="")

    # ── Look up registered repository ────────────────────
    repo = db.query(Repository).filter_by(
        full_name=payload.repository.full_name,
        is_active=True,
    ).first()

    if not repo:
        logger.info(f"Repo not registered: {payload.repository.full_name}")
        raise HTTPException(
            status_code=404,
            detail=f"Repository '{payload.repository.full_name}' is not registered in DevPulse.",
        )

    # ── Upsert PullRequest record ─────────────────────────
    pr = db.query(PullRequest).filter_by(
        repository_id=repo.id,
        pr_number=payload.pull_request.number,
    ).first()

    if not pr:
        pr = PullRequest(
            repository_id=repo.id,
            pr_number=payload.pull_request.number,
            title=payload.pull_request.title,
            author=payload.pull_request.user.login,
            base_branch=payload.pull_request.base.get("ref", "main"),
            head_branch=payload.pull_request.head.get("ref", ""),
            github_url=payload.pull_request.html_url,
            status="pending",
        )
        db.add(pr)
        db.commit()
        db.refresh(pr)
        logger.info(f"Created PR record: {repo.full_name}#{pr.pr_number}")
    else:
        # Re-queue on synchronize (new commits pushed)
        pr.status = "pending"
        db.commit()
        logger.info(f"Re-queued PR: {repo.full_name}#{pr.pr_number}")

    # ── Dispatch Celery task ──────────────────────────────
    # Import here to avoid circular imports
    from celery import Celery

    celery_app = Celery(
        "devpulse",
        broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    )

    task = celery_app.send_task("tasks.review_pr", args=[pr.id])

    # Save task ID back to PR
    pr.celery_task_id = task.id
    pr.status = "processing"
    db.commit()

    logger.info(f"Dispatched task {task.id} for PR #{pr.pr_number}")

    return PRResponse(
        message=f"PR #{pr.pr_number} queued for review",
        pr_id=pr.id,
        task_id=task.id,
    )


@router.get("/github/test")
async def webhook_test():
    """Simple endpoint to verify the webhook router is working."""
    return {"status": "webhook router is live"}
