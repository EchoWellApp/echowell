# EchoWell MVP

EchoWell watches for changes in a resident's voice over time. A device in the resident's room extracts voice measurements on the device (no audio leaves it); the backend screens each check-in, builds a personal baseline, scores daily deviation and runs a CUSUM persistence rule, and the dashboard shows staff which residents to check in with. Residents are identified by study IDs only.

EchoWell is a research system, not a medical device; it detects a change and prompts a check-in, it does not diagnose.

## Local quick start

Requires Docker 24+ with Compose v2 (TRD 15 §4.2; full procedure in [docs/deployment.md](docs/deployment.md)):

```sh
cp .env.development.example .env
docker compose up --build -d
curl -fsS http://localhost:8000/api/v1/health   # {"status":"ok","database":"ok",...}
```

The frontend runs at http://localhost:3000. Tools outside containers: Python 3.12 (`pip install -r backend/requirements.txt -r backend/requirements-dev.txt`, then `pytest -q`) and Node.js 20 (`cd frontend && npm ci && npm run test`).

## Documentation

- Requirements: [specs/TRD/](specs/TRD/) (TRD 00–25; TRD 24 holds open questions and decisions).
- Design and guides: [docs/](docs/) ([docs/design/](docs/design/), [docs/reports/](docs/reports/)).
- Backlog and roadmap: [specs/backlog/](specs/backlog/).
