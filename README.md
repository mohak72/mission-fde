# Incident Copilot — Mission FDE

![CI](https://github.com/mohak72/mission-fde/actions/workflows/ci.yaml/badge.svg)

Alert → runbook RAG → `kubectl` investigate → propose → human approves. The first of six products built over six months, documented in [`docs/`](docs/).

## Structure

Monorepo: `platform/` is shared code (LLM gateway, tracing) that M2–M6 will reuse as-is; `apps/incident-copilot/` is this specific product. See [docs/architecture/source-tree.md](docs/architecture/source-tree.md) for the full rationale and target layout.

## Local setup

Each package (`apps/incident-copilot/`, `platform/`) manages its own dependencies with [`uv`](https://github.com/astral-sh/uv).

```bash
cd apps/incident-copilot
uv sync
uv run uvicorn incident_copilot.main:app --reload
```

The app serves `GET /health` at `http://localhost:8000/health`.

Local Postgres + Chroma (needed from Story 1.2/1.3 onward) are available via:

```bash
docker-compose up -d
```

## Tests and linting

Run from within either package directory (`apps/incident-copilot/` or `platform/`):

```bash
uv run pytest          # tests
uv run ruff check .    # lint
uv run bandit -r src -c pyproject.toml   # security lint
uv run pip-audit       # dependency vulnerability scan
```

All four run in CI on every push/PR (see `.github/workflows/ci.yaml`), as separate jobs so a failure is attributable to a specific tier.

## Documentation

- [PRD](docs/prd/index.md)
- [Architecture](docs/architecture/index.md)
- [Stories](docs/stories/)
