# MineGuard AI deployment audit

## Frontend framework

Vite 6, React 18, TypeScript, React Router, Three.js and React Three Fiber. Entry: `frontend/src/main.tsx`. Build: `cd frontend && npm ci && npm run build`; output: `frontend/dist`.

## Backend framework

FastAPI, Uvicorn and SQLAlchemy. Entry: `backend.app.main:app`.

## Database

SQLite for local development. Production PostgreSQL is supported through `DATABASE_URL` using psycopg. Local SQLite files are ignored and must not be used as production persistence.

## Required environment variables

- Frontend: `VITE_API_BASE_URL`, `VITE_WS_URL`.
- Backend: `APP_ENV=production`, `DATABASE_URL`, `CORS_ORIGINS`, `MINEGUARD_ADMIN_TOKEN`.
- Optional: `MQTT_ENABLED`, `MODEL_PATH`; missing ML artifacts retain the rule fallback.

## Vercel compatibility

The Vite frontend is compatible and has SPA rewrites. The complete backend is not a suitable Vercel Functions workload because live operation uses persistent WebSockets, a long-running simulator and persistent state. The supported architecture is Vercel frontend plus a persistent FastAPI host and managed PostgreSQL. Polling remains the browser fallback.

## Problems discovered

- The folder was not a Git repository and had no deployment configuration or workflows.
- GitHub CLI authentication for `starck7777` is invalid.
- No production PostgreSQL database or persistent backend host is configured.
- Frontend production fallbacks referenced localhost.
- The old environment example contained an unsafe admin-password example.
- No login route exists. Placement mutation is server-token protected; public pages are read-only.
- Leaflet is not installed; the project uses its offline engineering map.
- Three.js creates a non-blocking large-chunk warning.
- No Python or frontend lint configuration exists; compilation, tests and build are current quality gates.

## Changes implemented

- Centralized frontend runtime endpoints and removed production localhost fallbacks.
- Added Vercel frontend SPA configuration.
- Added PostgreSQL configuration, URL normalization, environment CORS and production-safe admin behavior.
- Expanded `.gitignore` and replaced `.env.example` with safe examples.
- Added production README and deployment documentation.

## Verification results

- Backend tests: 7 passed.
- Frontend tests: 2 passed.
- TypeScript and Vite production build: passed.
- Health, public status, seed, simulator and coverage APIs were checked locally.
- Deployment is blocked pending GitHub re-authentication, managed PostgreSQL and a persistent backend URL.
