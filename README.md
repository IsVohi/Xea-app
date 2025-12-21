# Xea

**Verifiable governance intelligence powered by decentralized inference**

Xea produces verifiable governance intelligence by decomposing DAO proposals into atomic claims, validating them via redundant decentralized inference (PoI/PoUW), and producing signed, machine-verifiable evidence bundles and attestations.

## Quickstart

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for local backend development)

### Running with Docker Compose

```bash
# Clone the repository
git clone https://github.com/your-org/xea-governance-oracle.git
cd xea-governance-oracle

# Copy environment configuration
cp .env.example .env

# Start all services
docker-compose up --build
```

Services will be available at:
- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

### Local Development

```bash
# Backend
cd backend
pip install -e .
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Workers
cd workers
python worker.py
```

## Documentation

- [SPEC.md](./SPEC.md) — Full specification with data models, endpoints, and acceptance criteria
- [docs/demo_script.md](./docs/demo_script.md) — Demo walkthrough
- [docs/how_to_validate.md](./docs/how_to_validate.md) — Validation guide

## Project Structure

```
/
├── backend/           # FastAPI backend application
├── frontend/          # React frontend application
├── workers/           # RQ workers and mock miners
├── infra/             # Docker and deployment configs
├── contracts/         # Solidity attestation contracts (placeholder)
├── tests/             # Test suite
└── docs/              # Documentation
```

## Demo Script

See [docs/demo_script.md](./docs/demo_script.md) for a step-by-step demo walkthrough.

## License

MIT — see [LICENSE](./LICENSE)
