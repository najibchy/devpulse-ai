from django.db import models


class Repository(models.Model):
    """A GitHub repository registered for PR review."""

    owner = models.CharField(max_length=255, help_text="GitHub username or org name")
    name = models.CharField(max_length=255, help_text="Repository name")
    full_name = models.CharField(max_length=512, unique=True, help_text="owner/name")
    is_active = models.BooleanField(default=True, help_text="Enable/disable reviews for this repo")
    webhook_secret = models.CharField(max_length=255, blank=True, help_text="GitHub webhook secret")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Repositories"
        ordering = ["-created_at"]

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        self.full_name = f"{self.owner}/{self.name}"
        super().save(*args, **kwargs)


class PullRequest(models.Model):
    """A GitHub Pull Request that has been received via webhook."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        REVIEWED = "reviewed", "Reviewed"
        FAILED = "failed", "Failed"

    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name="pull_requests")
    pr_number = models.IntegerField(help_text="GitHub PR number")
    title = models.CharField(max_length=512)
    author = models.CharField(max_length=255, help_text="GitHub username of PR author")
    base_branch = models.CharField(max_length=255, default="main")
    head_branch = models.CharField(max_length=255)
    github_url = models.URLField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    celery_task_id = models.CharField(max_length=255, blank=True, help_text="Celery task ID for tracking")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("repository", "pr_number")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.repository.full_name}#{self.pr_number} — {self.title}"


class Review(models.Model):
    """An AI-generated review for a Pull Request."""

    pull_request = models.OneToOneField(PullRequest, on_delete=models.CASCADE, related_name="review")

    # Structured review output from LangGraph agent
    summary = models.TextField(help_text="High-level summary of the PR")
    bugs = models.JSONField(default=list, help_text="List of potential bugs found")
    suggestions = models.JSONField(default=list, help_text="List of improvement suggestions")
    security_issues = models.JSONField(default=list, help_text="Security concerns")
    complexity_score = models.IntegerField(
        null=True, blank=True,
        help_text="Estimated complexity score 1-10"
    )
    overall_verdict = models.CharField(
        max_length=20,
        choices=[
            ("approve", "Approve"),
            ("request_changes", "Request Changes"),
            ("comment", "Comment Only"),
        ],
        default="comment",
    )
    raw_llm_response = models.TextField(blank=True, help_text="Full raw response from LLM")
    tokens_used = models.IntegerField(default=0)
    model_used = models.CharField(max_length=100, default="gpt-4o-mini")
    posted_to_github = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.pull_request}"

    @property
    def bug_count(self):
        return len(self.bugs)

    @property
    def suggestion_count(self):
        return len(self.suggestions)


class ReviewEmbedding(models.Model):
    """Vector embedding of a review for semantic similarity search."""

    review = models.OneToOneField(Review, on_delete=models.CASCADE, related_name="embedding")
    # Stored as JSON array; pgvector column managed by SQLAlchemy/Alembic on FastAPI side
    embedding_json = models.JSONField(help_text="1536-dim OpenAI embedding vector as JSON array")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Embedding for review {self.review_id}"
