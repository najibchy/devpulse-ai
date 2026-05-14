# Deploying DevPulse AI to Railway

Railway is the fastest way to get DevPulse AI running in the cloud.
It supports Docker Compose natively and provides free PostgreSQL and Redis.

## Prerequisites
- Railway account: https://railway.app
- Railway CLI: `npm install -g @railway/cli`
- GitHub repo with DevPulse AI pushed to `main`

## Steps

### 1. Login to Railway
```bash
railway login
```

### 2. Create a new project
```bash
railway init
# Choose: "Empty project"
# Name it: devpulse-ai
```

### 3. Add PostgreSQL
In the Railway dashboard:
- Click **+ New** → **Database** → **PostgreSQL**
- Railway auto-sets `DATABASE_URL` in your environment

### 4. Add Redis
- Click **+ New** → **Database** → **Redis**
- Railway auto-sets `REDIS_URL` in your environment

### 5. Set environment variables
In Railway dashboard → your project → **Variables**, add:

```
DJANGO_SECRET_KEY=your_long_random_secret
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-project.up.railway.app
GITHUB_WEBHOOK_SECRET=your_webhook_secret
GITHUB_APP_TOKEN=ghp_your_token
OPENAI_API_KEY=sk-your_key
LLM_MODEL=gpt-4o-mini
ENVIRONMENT=production
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<from Railway>
POSTGRES_DB=railway
```

### 6. Deploy each service
Railway deploys each service from its Dockerfile.
Add 3 services in the dashboard:

**Service 1 — API**
- Source: GitHub repo, root path `/services/api`
- Port: 8000

**Service 2 — Dashboard**
- Source: GitHub repo, root path `/services/dashboard`
- Port: 8080

**Service 3 — Worker**
- Source: GitHub repo, root path `/services/worker`
- Start command: `celery -A tasks worker --loglevel=info --concurrency=2 -Q review,default`

### 7. Configure GitHub Webhook
Once your API service is deployed and has a public URL:

1. Go to your GitHub repo → **Settings** → **Webhooks** → **Add webhook**
2. Payload URL: `https://your-api.up.railway.app/webhook/github`
3. Content type: `application/json`
4. Secret: same value as `GITHUB_WEBHOOK_SECRET`
5. Events: select **Pull requests** only
6. Click **Add webhook**

### 8. Register your repo in Django Admin
1. Open `https://your-dashboard.up.railway.app/admin`
2. Login: `admin` / `admin123` (change immediately!)
3. Go to **Repositories** → **Add Repository**
4. Enter your GitHub `owner` and repo `name`
5. Set **Is active**: ✅

### 9. Test it
Open a Pull Request in your registered repo.
Within seconds you should see a DevPulse AI comment appear on the PR!

---

## Alternative: DigitalOcean Droplet

For more control, deploy to a $6/month DigitalOcean droplet:

```bash
# On your droplet (Ubuntu 24.04)
sudo apt update && sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER

# Clone your repo
git clone https://github.com/yourusername/devpulse-ai.git
cd devpulse-ai

# Set up env
cp .env.production.example .env
nano .env  # fill in all values

# Pull images built by GitHub Actions CD pipeline
docker compose -f docker-compose.prod.yml pull

# Start everything
docker compose -f docker-compose.prod.yml up -d

# Check logs
docker compose -f docker-compose.prod.yml logs -f
```

Then point your domain / webhook URL at the droplet's IP on port 8000.