from prompts import REVIEW_PROMPT, SYSTEM_PROMPT


def test_review_prompt_formatting():
    filled = REVIEW_PROMPT.format(
        repo_full_name="org/repo",
        pr_number=42,
        pr_title="Add login feature",
        pr_description="Implements OAuth2 login",
        diff="+ def login(): pass",
    )
    assert "org/repo" in filled
    assert "Add login feature" in filled
    assert "def login" in filled


def test_system_prompt_not_empty():
    assert len(SYSTEM_PROMPT) > 50
