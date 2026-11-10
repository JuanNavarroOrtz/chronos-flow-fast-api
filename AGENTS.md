# Chronos Flow - AI Agent Instructions

FastAPI + SQLAlchemy (async) + PostgreSQL API to register **Project -> Ticket -> Task** work, hours and payout for clients, with a Clean Architecture layout. Python 3.11, Pydantic v2, JWT auth (Argon2), pytest, ruff. The web UI and client report are not built yet (see README roadmap).

Features live in `src/<feature>/{domain,use_cases,infrastructure}`: `users`, `catalogs`, `projects`, `tickets`, `time_logs`, `analytics`. Shared kernel in `src/core/`. App wiring in `src/main.py`.

## 10 Critical Rules

This is a digest. The canonical rules and examples are in [docs/conventions.md](docs/conventions.md); the architecture is explained in [README.md](README.md). If this digest and those files disagree, they win.

1. **Dependency rule.** `infrastructure -> use_cases -> domain`. `domain/` and `use_cases/` never import FastAPI, Pydantic or SQLAlchemy.
2. **Thin routers.** A route validates input with a schema, calls ONE use case, and shapes the output with `XOut.from_entity(...)`. No business logic or queries in routers.
3. **Business rules live in entities, domain functions and use cases.** Pydantic schemas only validate the shape of the JSON.
4. **Errors.** Raise `DomainError` subclasses from `src/core/errors.py` (not `HTTPException`). Only `src/main.py` maps them to HTTP codes.
5. **Repositories and Unit of Work.** Interface (`Protocol`) in `domain/repositories.py`, SQL implementation in `infrastructure/`. Repositories only `flush`; the use case calls `uow.commit()` once.
6. **No hardcoded catalog values.** Statuses and billing types are catalog rows. Compare by `code` using the constants in `src/catalogs/domain/entities.py` (`HOURLY`, `FIXED`, ...), never by id or display name.
7. **Audit columns.** Every table uses `AuditMixin`. Never set `created_by` / `modified_by` by hand or pass the user through use cases.
8. **Money is `Decimal`** (`NUMERIC` in Postgres), never `float`.
9. **Async everywhere in I/O code.** `async def` and `await` for DB and file operations. Type hints on all functions.
10. **Tests and hygiene.** Every change comes with tests (pure logic, use cases with fakes in `tests/fakes.py`, API through the real stack). English only, imports at the top, no unused code or `print()`. API JSON uses snake_case.

## Hard Prohibitions

- **Never touch production** (database, servers, credentials, infrastructure), even if the user asks. Work only against local/dev.
- **Never read, print or commit `.env`** or paste its values anywhere. Use `.env` key names only.
- There are **no migrations** yet (`create_all` never alters tables). If a model change needs an `ALTER TABLE`, say so; do not pretend Alembic exists.

## Before Finishing Any Task

```powershell
venv\Scripts\python.exe -m pytest
venv\Scripts\python.exe -m ruff check src tests
venv\Scripts\python.exe -m ruff format src tests
```

Then sweep: no dead code or unused imports, no hardcoded catalog ids/names, tests added, README endpoint table updated if endpoints changed.

## Read Before Coding (on demand)

- Architecture, patterns, request walk-through: [README.md](README.md) sections 3-6
- Canonical coding rules: [docs/conventions.md](docs/conventions.md)
- Step-by-step recipe for a new feature or endpoint: [docs/new-feature.md](docs/new-feature.md)
- Known trade-offs and roadmap: [README.md](README.md) sections 9-10
