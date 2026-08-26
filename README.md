# MineGuard AI

MineGuard AI is an educational hybrid digital-twin prototype for coal-mine subsidence monitoring. It combines live or simulated telemetry, explainable risk analytics, device coverage, a mine prototype twin and an interactive sensor-node hardware model.

> MineGuard AI is not certified operational mine-safety equipment. Prototype thresholds, coverage estimates and hobby-grade measurements require mine-specific surveys, geotechnical validation and certified equipment.

## Problem and solution

Subsidence indicators are difficult to interpret when readings, placement, communications and ground risk are mixed together. MineGuard keeps individual sensor risk, ground risk, device health, data quality and LoRa quality separate while preserving every reading's location and provenance.

## Features

- Live command-centre overview with REAL/SIMULATED provenance.
- Sensor-level analytics, explanations, charts and exports.
- Sectors, landmarks, gateways, depths and local coordinates.
- Separate communication estimates, local measurements and risk zones.
- 3D mine prototype and procedural ESP32 sensor-node model.
- WebSocket updates with reconnect, sequence validation and polling fallback.
- Rule-based inference when optional ML artifacts are unavailable.
- Demonstration simulator and privacy-reduced public status.

## Pages

| Route | Purpose |
|---|---|
| `/` | Command centre and simulator |
| `/module-analytics` | Module and sensor analytics |
| `/device-coverage` | Sector, landmark, gateway and placement coverage |
| `/map` | Live mine map |
| `/digital-twin-3d` | Complete tabletop mine prototype |
| `/hardware-model-3d` | Interactive sensor-node hardware |
| `/public` | Public read-only status |

## Hardware

The prototype models solar supply, protected 18650 batteries, ESP32, SX1276/78 LoRa, VL53L1X, MPU6050, ADXL345, capacitive relative-moisture probe, protected SHT31, optional load cell/HX711, beacon, enclosure, ground plate and stake. See [prototype assembly](hardware/PROTOTYPE_BUILD.md) and the [printable exploded drawing](hardware/sensor-node-exploded.svg).

## Stack and architecture

- Frontend: React 18, TypeScript, Vite, React Router, Three.js and React Three Fiber.
- Backend: Python, FastAPI, Pydantic and SQLAlchemy.
- Storage: SQLite locally; PostgreSQL required for production.
- Live transport: WebSocket with REST polling fallback.

```text
ESP32/Simulator → FastAPI ingestion → SQLAlchemy/PostgreSQL
                         ├─ REST analytics → React/Vite on Render
                         └─ WebSocket live stream ─────────────┘
```

## Screenshots

Reviewed screenshots of Module Analytics, Device Coverage and the Hardware Model should be added before a public release. Generated screenshots are not committed currently.

## Local setup

Requires Python 3.11+ and Node.js 20+.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
uvicorn backend.app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`; API documentation is at `http://127.0.0.1:8000/docs`.

## Configuration, database and simulator

See [.env.example](.env.example). `VITE_` variables are public and must not contain secrets. Production requires `DATABASE_URL`, `CORS_ORIGINS`, `MINEGUARD_ADMIN_TOKEN`, `VITE_API_BASE_URL` and `VITE_WS_URL`.

The backend initializes tables and fictional demonstration records idempotently. Production must use managed PostgreSQL. Start a simulation from the overview or:

```bash
curl -X POST http://127.0.0.1:8000/api/simulator/start \
  -H 'content-type: application/json' \
  -d '{"scenario":"gradual_subsidence","intensity":1,"speed":1,"node_code":"all"}'
```

Generated telemetry remains labelled SIMULATED. Training does not run during builds or ordinary requests.

## Tests

```bash
.venv312/bin/python -m pytest backend/tests -q
cd frontend
npm run typecheck
npm run test
npm run build
```

## Deployment

The production Blueprint builds React and serves it from the persistent FastAPI service on Render, backed by managed PostgreSQL. See [deployment instructions](docs/DEPLOYMENT.md) and [deployment audit](DEPLOYMENT_AUDIT.md).

- Live application: provision with the Render Blueprint below.
- API documentation: available at `/docs` on the deployed application.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2Fstarck7777%2Fmineguard-ai)

This project is an SIH educational prototype and must not be represented as a certified underground warning system.
