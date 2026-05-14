import os

import django
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DATABASE_URL", "postgresql://devpulse:devpulse_secret@localhost:5432/devpulse")
os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key")


@pytest.fixture(autouse=True)
def setup_django():
    django.setup()


def test_repository_str():
    from core.models import Repository
    repo = Repository(owner="acme", name="api")
    repo.full_name = "acme/api"
    assert str(repo) == "acme/api"


def test_pull_request_str():
    from core.models import PullRequest, Repository
    repo = Repository(owner="acme", name="api")
    repo.full_name = "acme/api"
    pr = PullRequest(repository=repo, pr_number=7, title="Fix bug")
    assert "acme/api" in str(pr)
    assert "7" in str(pr)
