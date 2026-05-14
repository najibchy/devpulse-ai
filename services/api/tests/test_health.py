import os
import sys

# Set required env vars BEFORE any imports that read them
os.environ.setdefault("DATABASE_URL", "postgresql://devpulse:devpulse_secret@localhost:5432/devpulse")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-placeholder")
os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "test-secret")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_health():
    with patch("sqlalchemy.create_engine", return_value=MagicMock()):
        from main import app
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_webhook_test_endpoint():
    with patch("sqlalchemy.create_engine", return_value=MagicMock()):
        from main import app
        client = TestClient(app)
        response = client.get("/webhook/github/test")
        assert response.status_code == 200
