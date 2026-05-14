import logging
import os

import httpx

logger = logging.getLogger(__name__)

GITHUB_APP_TOKEN = os.getenv("GITHUB_APP_TOKEN", "")
GITHUB_API = "https://api.github.com"

HEADERS = {
    "Authorization": f"Bearer {GITHUB_APP_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def get_pr_diff(full_name: str, pr_number: int) -> str:
    """Fetch the unified diff for a pull request."""
    url = f"{GITHUB_API}/repos/{full_name}/pulls/{pr_number}"
    headers = {**HEADERS, "Accept": "application/vnd.github.v3.diff"}

    with httpx.Client(timeout=30) as client:
        response = client.get(url, headers=headers)

    if response.status_code != 200:
        logger.error(f"Failed to fetch diff: {response.status_code} {response.text}")
        raise RuntimeError(f"GitHub API error {response.status_code}: {response.text}")

    return response.text


def get_pr_details(full_name: str, pr_number: int) -> dict:
    """Fetch PR metadata (title, description, author, etc.)."""
    url = f"{GITHUB_API}/repos/{full_name}/pulls/{pr_number}"

    with httpx.Client(timeout=30) as client:
        response = client.get(url, headers=HEADERS)

    if response.status_code != 200:
        raise RuntimeError(f"GitHub API error {response.status_code}: {response.text}")

    data = response.json()
    return {
        "title": data["title"],
        "body": data.get("body") or "",
        "author": data["user"]["login"],
        "base_branch": data["base"]["ref"],
        "head_branch": data["head"]["ref"],
        "changed_files": data["changed_files"],
        "additions": data["additions"],
        "deletions": data["deletions"],
        "html_url": data["html_url"],
    }


def post_pr_comment(full_name: str, pr_number: int, body: str) -> bool:
    """Post a comment on a pull request."""
    url = f"{GITHUB_API}/repos/{full_name}/issues/{pr_number}/comments"

    with httpx.Client(timeout=30) as client:
        response = client.post(url, headers=HEADERS, json={"body": body})

    if response.status_code == 201:
        logger.info(f"Posted comment on {full_name}#{pr_number}")
        return True

    logger.error(f"Failed to post comment: {response.status_code} {response.text}")
    return False


def format_review_comment(review: dict) -> str:
    """Format the LLM review output as a GitHub markdown comment."""
    verdict_emoji = {
        "approve": "✅",
        "request_changes": "🔴",
        "comment": "💬",
    }.get(review.get("overall_verdict", "comment"), "💬")

    bugs = review.get("bugs", [])
    suggestions = review.get("suggestions", [])
    security = review.get("security_issues", [])
    score = review.get("complexity_score", "N/A")

    bugs_md = "\n".join(f"- {b}" for b in bugs) if bugs else "_None found_"
    suggestions_md = "\n".join(f"- {s}" for s in suggestions) if suggestions else "_None_"
    security_md = "\n".join(f"- {s}" for s in security) if security else "_None found_"

    return f"""## {verdict_emoji} DevPulse AI Review

### Summary
{review.get("summary", "")}

---

### 🐛 Potential Bugs
{bugs_md}

### 💡 Suggestions
{suggestions_md}

### 🔒 Security Issues
{security_md}

---

**Complexity Score:** {score}/10
**Model:** `{review.get("model_used", "gpt-4o-mini")}`

_Reviewed by [DevPulse AI](https://github.com/devpulse-ai) 🤖_
"""
