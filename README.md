# DevPulse AI

> Intelligent Code Review & PR Summary Agent

DevPulse AI automatically reviews GitHub Pull Requests using LLMs. When a PR is opened,
it fetches the diff, runs a multi-step LangGraph agent, posts a structured review comment
on GitHub, and stores the review with vector embeddings for semantic search.

![CI](https://github.com/najibchy/devpulse-ai/actions/workflows/ci.yml/badge.svg)

---

## Features

- **Automatic PR reviews** — triggered by GitHub webhooks on `opened` and `synchronize`
- **Structured output** — bugs, suggestions, security issues, complexity score, verdict
- **Semantic memory** — pgvector stores embeddings of past reviews; similar PRs get richer context
- **Django admin** — register repos, monitor PRs, view review history
- **Celery task queue** — async processing with retries and failure handling
- **Flower dashboard** — real-time task monitoring

## Tech Stack

| Layer | Technology |
|---|---|
| Web API | FastAPI |
| Admin Dashboard | Django + Django Admin |
| Task Queue | Celery + Redis |
| AI Agent | LangGraph (multi-step) |
| LLM | OpenAI GPT-4o-mini |
| Vector Search | PostgreSQL + pgvector |
| Database ORM | SQLAlchemy + Alembic |
| Containerisation | Docker + Docker Compose |
| CI/CD | GitHub Actions → GHCR |
| Cloud | Railway / DigitalOcean |

## Architecture

```
GitHub PR opened
      │
      ▼
 FastAPI :8000          ← verifies webhook signature
      │  enqueue task
      ▼
    Redis               ← Celery broker
      │
      ▼
 Celery Worker
      ├── GitHub API    ← fetch diff + PR metadata
      ├── pgvector      ← search similar past reviews
      ├── LangGraph     ← multi-step review agent
      │     └── OpenAI  ← GPT-4o-mini structured JSON
      ├── PostgreSQL    ← save review
      ├── pgvector      ← store new embedding
      └── GitHub API    ← post review comment
            │
Django :8080            ← admin dashboard for repos + reviews
Flower :5555            ← Celery task monitor
```

## Getting Started

### Prerequisites
- Docker & Docker Compose
- A GitHub Personal Access Token (repo + PR comment permissions)
- An OpenAI API key

### Local Setup

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/devpulse-ai.git
cd devpulse-ai

# 2. Configure
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY and GITHUB_APP_TOKEN

# 3. Start all services
docker compose up --build

# 4. Open services
#   FastAPI docs:   http://localhost:8000/docs
#   Django admin:   http://localhost:8080/admin  (admin / admin123)
#   Flower:         http://localhost:5555
```

### Register a Repository

1. Open Django admin → **Repositories** → **Add Repository**
2. Enter your GitHub `owner` and repo `name`
3. Set **Is active** to ✅

### Configure GitHub Webhook

1. GitHub repo → **Settings** → **Webhooks** → **Add webhook**
2. Payload URL: `http://your-server:8000/webhook/github`
3. Content type: `application/json`
4. Secret: value of `GITHUB_WEBHOOK_SECRET` in your `.env`
5. Events: **Pull requests** only

### Open a PR — watch the magic happen 🎉

## Project Structure

```
devpulse-ai/
├── services/
│   ├── api/                  # FastAPI — webhook receiver + REST
│   │   ├── main.py
│   │   ├── schemas.py
│   │   ├── routers/webhook.py
│   │   └── db/               # SQLAlchemy models + Alembic migrations
│   ├── dashboard/            # Django — admin + models
│   │   ├── config/           # Django settings
│   │   └── core/             # models, admin, management commands
│   └── worker/               # Celery — async task processing
│       ├── tasks.py          # review_pr task orchestrator
│       ├── agent.py          # LangGraph review agent
│       ├── vector_store.py   # pgvector embed + search
│       ├── github.py         # GitHub API client
│       └── prompts.py        # LLM prompt templates
├── .github/workflows/
│   ├── ci.yml                # Lint + test on every push
│   └── cd.yml                # Build + push Docker images on main
├── docker-compose.yml        # Local development
├── docker-compose.prod.yml   # Production
└── deploy/railway.md         # Deployment guide
```

## Deployment

See [deploy/railway.md](deploy/railway.md) for full instructions.

Quick deploy to DigitalOcean:

```bash
cp .env.production.example .env  # fill in secrets
docker compose -f docker-compose.prod.yml up -d
```

## License

MIT