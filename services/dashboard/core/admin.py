from django.contrib import admin
from django.utils.html import format_html

from .models import PullRequest, Repository, Review


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ("full_name", "owner", "is_active", "pr_count", "created_at")
    list_filter = ("is_active",)
    search_fields = ("owner", "name", "full_name")
    readonly_fields = ("full_name", "created_at", "updated_at")
    fieldsets = (
        ("Repository", {"fields": ("owner", "name", "full_name", "is_active")}),
        ("Webhook", {"fields": ("webhook_secret",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def pr_count(self, obj):
        return obj.pull_requests.count()
    pr_count.short_description = "PRs"


class ReviewInline(admin.StackedInline):
    model = Review
    readonly_fields = (
        "summary", "bugs", "suggestions", "security_issues",
        "complexity_score", "overall_verdict", "tokens_used",
        "model_used", "posted_to_github", "created_at",
    )
    extra = 0
    can_delete = False


@admin.register(PullRequest)
class PullRequestAdmin(admin.ModelAdmin):
    list_display = (
        "pr_number", "repository", "title", "author",
        "status_badge", "head_branch", "created_at",
    )
    list_filter = ("status", "repository")
    search_fields = ("title", "author", "head_branch")
    readonly_fields = ("celery_task_id", "created_at", "updated_at", "github_link")
    inlines = [ReviewInline]
    fieldsets = (
        ("Pull Request", {
            "fields": ("repository", "pr_number", "title", "author", "github_link")
        }),
        ("Branches", {"fields": ("base_branch", "head_branch")}),
        ("Status", {"fields": ("status", "celery_task_id")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def status_badge(self, obj):
        colors = {
            "pending": "#f59e0b",
            "processing": "#3b82f6",
            "reviewed": "#10b981",
            "failed": "#ef4444",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"

    def github_link(self, obj):
        return format_html('<a href="{}" target="_blank">{}</a>', obj.github_url, obj.github_url)
    github_link.short_description = "GitHub URL"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "pull_request", "overall_verdict", "bug_count",
        "complexity_score", "tokens_used", "posted_to_github", "created_at",
    )
    list_filter = ("overall_verdict", "posted_to_github", "model_used")
    readonly_fields = ("created_at", "raw_llm_response", "tokens_used", "model_used")
    fieldsets = (
        ("Review", {"fields": ("pull_request", "summary", "overall_verdict", "complexity_score")}),
        ("Findings", {"fields": ("bugs", "suggestions", "security_issues")}),
        ("Meta", {"fields": ("model_used", "tokens_used", "posted_to_github", "created_at")}),
        ("Raw Response", {"fields": ("raw_llm_response",), "classes": ("collapse",)}),
    )

    def bug_count(self, obj):
        count = obj.bug_count
        if count > 0:
            return format_html('<span style="color:#ef4444;font-weight:bold">{} bugs</span>', count)
        return format_html('<span style="color:#10b981">✓ Clean</span>')
    bug_count.short_description = "Bugs"


admin.site.site_header = "DevPulse AI"
admin.site.site_title = "DevPulse AI Admin"
admin.site.index_title = "PR Review Dashboard"
