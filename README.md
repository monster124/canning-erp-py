# canning-erp-py

ERP for canned-food production - Python rewrite of the Go `canning-erp` backend
(FastAPI + PostgreSQL 16 + Redis 7, database-per-tenant).

## Stack

- Python 3.13, FastAPI + Uvicorn (async)
- SQLAlchemy 2 (async) + asyncpg, Alembic
- PostgreSQL 16 (database-per-tenant), Redis 7 (rate-limit, tenant cache)
- Security: argon2id (passwords), AES-GCM (field encryption), PyJWT (access/refresh)
- Export: openpyxl (xlsx), reportlab (pdf)
- Realtime: SSE (sse-starlette), metrics: prometheus-client
- Quality: ruff + mypy (strict on domain/application) + pytest

## Architecture (Clean Architecture)

```
interfaces -> application -> domain <- infrastructure
```

- `domain` - entities, business rules, ports (zero external imports)
- `application` - use-cases, depends only on ports
- `infrastructure` - SQLAlchemy/asyncpg, Redis, JWT, argon2, AES-GCM, export
- `interfaces` - FastAPI routers, middleware, DTOs, error mapping

## Quick start (P0)

```bash
apt install python3.13 python3.13-venv libpq-dev postgresql redis-server git
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
uv run pytest
uv run uvicorn canning_erp.interfaces.http.app:create_app --factory --reload
```

## Roadmap

P0 scaffold (this commit) -> P1 domain-core -> P2 infra-core -> P3 auth ->
P4 interfaces-core -> P5 inventory API -> P6 bom+production -> P7 mrp+procurement ->
P8 reports+traceability -> P9 realtime -> P10 admin+fin (tag v0.1.0).
