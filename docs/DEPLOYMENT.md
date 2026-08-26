# Deployment

## Architecture

```text
Browser → Vercel Vite frontend
              ├─ HTTPS → persistent FastAPI backend
              └─ WSS   → persistent FastAPI backend → managed PostgreSQL
```

Vercel hosts the frontend. FastAPI requires a persistent host because MineGuard uses WebSockets and a long-running simulator. Writable SQLite is local-only.

## URLs

- GitHub repository: pending GitHub CLI re-authentication.
- Vercel frontend and production URL: pending a verified backend deployment.
- API documentation: served from the backend at `/docs`.

## Variables

Frontend Vercel project:

```text
VITE_API_BASE_URL=https://your-api-host.example
VITE_WS_URL=wss://your-api-host.example/ws/live
```

Persistent backend:

```text
APP_ENV=production
DATABASE_URL=postgresql+psycopg://...
CORS_ORIGINS=https://your-project.vercel.app
MINEGUARD_ADMIN_TOKEN=<secret>
MQTT_ENABLED=false
MODEL_PATH=
```

Never commit actual values. `VITE_` variables are visible to browsers.

## Commands

```bash
cd frontend
npm ci
npm run typecheck
npm run test
npm run build
vercel link --yes --project mineguard-ai
vercel deploy
vercel inspect <preview-url>
vercel deploy --prod
vercel inspect <production-url>
vercel logs <production-url>
```

Configure the Vercel root directory as `frontend`, preset Vite, build `npm run build`, output `dist`, production branch `main`.

Backend startup:

```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT"
```

Tables and demonstration records initialize idempotently. Configure PostgreSQL before production traffic.

## Live updates, redeployment and rollback

The browser uses WebSockets with exponential reconnect and ten-second REST polling. Pushes to `main` can deploy production after Git integration; pull requests create previews. Use `vercel rollback` for the frontend and the database provider's backups for data rollback.

Troubleshooting: verify API/WS variables and CORS for blank data; configure PostgreSQL if data disappears after backend restarts; confirm `frontend/vercel.json` for nested-route 404s.
