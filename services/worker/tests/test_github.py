from unittest.mock import MagicMock, patch

import pytest
from github import format_review_comment


def test_format_review_comment_approve():
    review = {
        "summary": "Looks great overall.",
        "bugs": [],
        "suggestions": ["Consider adding more tests."],
        "security_issues": [],
        "complexity_score": 3,
        "overall_verdict": "approve",
        "model_used": "gpt-4o-mini",
    }
    comment = format_review_comment(review)
    assert "✅" in comment
    assert "Looks great overall." in comment
    assert "Consider adding more tests." in comment
    assert "gpt-4o-mini" in comment


def test_format_review_comment_request_changes():
    review = {
        "summary": "Has critical bugs.",
        "bugs": ["Null pointer on line 42"],
        "suggestions": [],
        "security_issues": ["SQL injection risk"],
        "complexity_score": 8,
        "overall_verdict": "request_changes",
        "model_used": "gpt-4o-mini",
    }
    comment = format_review_comment(review)
    assert "🔴" in comment
    assert "Null pointer on line 42" in comment
    assert "SQL injection risk" in comment


def test_format_review_comment_no_bugs():
    review = {
        "summary": "Minor suggestions only.",
        "bugs": [],
        "suggestions": [],
        "security_issues": [],
        "complexity_score": 2,
        "overall_verdict": "comment",
        "model_used": "gpt-4o-mini",
    }
    comment = format_review_comment(review)
    assert "_None found_" in comment
