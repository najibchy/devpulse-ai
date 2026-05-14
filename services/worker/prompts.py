SYSTEM_PROMPT = """You are DevPulse AI, an expert code reviewer with deep knowledge of
software engineering best practices, security, performance, and clean code principles.

Your reviews are:
- Precise and actionable (not vague)
- Constructive and professional
- Focused on real issues, not style nitpicks
- Security-conscious

You always respond in valid JSON only. No markdown, no explanation outside the JSON."""


REVIEW_PROMPT = """Review the following Pull Request and return a JSON object.

## PR Information
- Repository: {repo_full_name}
- PR #{pr_number}: {pr_title}
- Description: {pr_description}

## Diff
```diff
{diff}
```

## Instructions
Analyze the diff carefully and return ONLY a JSON object with this exact structure:

{{
  "summary": "2-3 sentence high-level summary of what this PR does and your overall impression",
  "bugs": [
    "Specific bug description with file/line context if possible",
    "Another bug if found"
  ],
  "suggestions": [
    "Concrete improvement suggestion",
    "Another suggestion"
  ],
  "security_issues": [
    "Security concern with explanation",
  ],
  "complexity_score": 5,
  "overall_verdict": "approve"
}}

Rules:
- "bugs": list of strings, empty list if none found
- "suggestions": list of strings, empty list if none
- "security_issues": list of strings, empty list if none
- "complexity_score": integer 1-10 (1=trivial, 10=very complex)
- "overall_verdict": exactly one of "approve", "request_changes", or "comment"
  - "approve" if the code looks good with minor or no issues
  - "request_changes" if there are bugs or security issues that must be fixed
  - "comment" if you have suggestions but nothing blocking

Return ONLY the JSON object. No other text."""


SIMILAR_REVIEWS_CONTEXT = """
## Similar Past Reviews (for context)
The following are summaries of similar PRs reviewed before. Use them to maintain
consistency in your reviews but do not copy them directly:

{similar_reviews}
"""
