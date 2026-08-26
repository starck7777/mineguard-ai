# MineGuard AI Bug Audit

Audit date: 2026-08-26. The supplied workspace was empty and not a Git repository; therefore no pre-existing runtime could be audited and no user code was removed.

| Bug ID | Module | Description | Steps to reproduce | Root cause | Severity | Fix implemented | Test added | Verification result |
|---|---|---|---|---|---|---|---|---|
| AUD-001 | Repository | Continuation target absent | `ls -la`; `git status` | Empty workspace | High | Created runnable baseline in requested workspace | Startup tests | Backend and frontend verified |
| API-001 | Telemetry | Duplicate packets could create repeated readings/alerts | POST same node and sequence twice | No existing ingestion layer | High | Unique `(node, sequence)` handling; duplicate returns existing result | `test_duplicate_packet` | Passed |
| API-002 | Telemetry | Impossible physical values could enter risk engine | POST battery=-1 | No validation | High | Pydantic bounds and central 422 handling | `test_invalid_battery` | Passed |
| API-003 | Reliability | Optional MQTT/ML absence could prevent startup | Start without broker/models | Hard dependency risk | High | Optional health states and rule fallback; no broker required | `test_health` | Passed; live health returned `ok` |
| API-004 | Alerts | Repeated readings could cause alert storms | Send sustained warning readings | Missing incident grouping | High | Node/severity dedupe and 60s cooldown | `test_alert_deduplication` | Automated test included |
| API-005 | Risk | Noisy threshold crossings cause flapping | Alternate scores around boundary | No hysteresis | Medium | Stateful 4-point hysteresis | `test_hysteresis` | Passed |
| API-006 | Privacy | Public endpoint could expose hardware/admin details | GET public status | No API boundary | High | Dedicated aggregate-only response | `test_public_privacy` | Passed |
| RT-001 | WebSocket | Navigation could create duplicate sockets/reconnect loops | Change routes repeatedly | Per-page connection patterns | High | App-level provider, cleanup, capped exponential backoff, polling fallback, sequence dedupe | Hook tests scaffolded | Typecheck/build required |
| UI-001 | Runtime | Component errors could blank app | Throw in routed child | No boundary | High | Global and scene-specific error boundaries with recovery | Component test | Automated test included |
| UI-002 | Data | Offline node could appear as ground-critical | Run offline scenario | Health/risk conflation | High | Grey connectivity presentation while retaining last ground risk separately | Risk utility test | Automated test included |
| UI-003 | 3D | WebGL loss could blank digital twin | Disable WebGL | No fallback | High | Capability check, scene boundary, live 2D cutaway | Component path | Production build passed; WebGL canvas verified |
| UI-004 | Charts | Empty/one-point data could fail | Backend unavailable/new database | Unsafe chart assumptions | Medium | Explicit empty state and SVG chart supporting one point | Component test | Automated test included |
| RT-002 | CORS | UI opened on `127.0.0.1` rendered but could not load API data | Start Vite with `--host 127.0.0.1` | Default allow-list contained only `localhost` | High | Allow both standard local development origins by default | Live browser check | Passed; `LIVE_NODE_DATA` and `LIVE_STATUS` |
| FW-001 | Motor | Unsafe reboot/motion beyond limits | Power cycle or command excessive travel | Missing fail-safe firmware | Critical | Disabled-on-boot, E-stop, dual limits, bounded travel, timeout | Documentation review | Firmware skeleton included |

Verification results are updated only after commands are actually run.

## Verification summary

- Backend: 5 tests passed in 1.23 s.
- Frontend: TypeScript passed; 1 unit test passed; Vite production build passed.
- Browser: overview meaningful-content and overlay checks passed; WebGL canvas, controls, layer toggles, and live node inspector rendered.
- End-to-end: sudden-movement simulator drove NODE-01 to -20.00 mm, updated the 3D inspector to Critical 100/100 over WebSocket, and created grouped ground-risk alerts.
- Known build note: the lazy Three.js route is 860 kB minified (231 kB gzip); it is isolated from the main 196 kB application chunk.
- Not run: physical ESP32/LoRa tests, firmware compilation (board toolchains absent), real MQTT broker, trained scikit-learn artifacts, PDF export, and full Playwright matrix.
