# Conventions - Chronos Flow

> Single source of truth for coding rules. The architecture and patterns are explained in `README.md`
> (sections 3-6); this file does not repeat them, it states what is allowed and what is not.

## 1. Layers and the dependency rule

| Layer | Folder | May import | Must NOT import |
|---|---|---|---|
| Domain | `domain/` | stdlib, `src.core.errors`, other features' `domain` | FastAPI, Pydantic, SQLAlchemy |
| Use cases | `use_cases/` | `domain`, `src.core.errors`, `src.core.unit_of_work` | FastAPI, Pydantic, SQLAlchemy |
| Infrastructure | `infrastructure/` | everything | - |

- Entities are plain Python objects with business rules and no database knowledge.
- Use cases depend on **ports** (`Protocol` classes in `domain/repositories.py`, `domain/storage.py`), never on SQL classes.
- Cross-feature access goes through the other feature's repository interface or use case, never through its ORM models.

## 2. Routers (`infrastructure/router.py`)

A route does exactly four things: receive a validated schema, call one use case, shape the response, return it.

```python
@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(body: ProjectCreate, uc: UseCases):
    return ProjectOut.from_entity(await uc.create(**body.model_dump()))
```

- Build use cases with a `get_<feature>_use_cases` dependency and the alias `UseCases = Annotated[..., Depends(...)]`.
- No business decisions, no queries, no `try/except` around use cases (errors are mapped in `main.py`).
- Every router except `auth` is registered in `main.py` with `dependencies=_protected`, so every endpoint needs a token.
- Response shape comes from `XOut.from_entity(entity)`; never return ORM models.

## 3. Validation: two different jobs

- **Shape and types** of the JSON (required fields, `Decimal`, dates, string length, regex): Pydantic schemas in `infrastructure/schemas.py`.
- **Business rules** (unique acronym, hourly project needs a rate, ticket belongs to the project): entities, domain functions and use cases, raising `DomainError`.

## 4. Errors

Raise subclasses of `DomainError` from `src/core/errors.py`:

| Error | HTTP |
|---|---|
| `NotFoundError` | 404 |
| `ConflictError`, `DuplicateError` | 409 |
| `InvalidDataError` | 422 |
| `UnauthorizedError` | 401 |
| `ForbiddenError` | 403 |

- Never raise `HTTPException` in `domain/` or `use_cases/`.
- To support a new error type, add the class in `errors.py` and add it to `_STATUS` in `src/main.py` (subclasses are matched with `isinstance`). Never build error responses in routers or use cases.
- Error messages are in English and say what happened ("Project 5 not found").

## 5. Persistence

- Repositories implement the `Protocol` in `domain/repositories.py`, map entity <-> ORM model, and only **stage** changes (`flush`).
- The use case calls `await self._uow.commit()` once at the end of the operation; if it fails before that, everything rolls back.
- Every table inherits `AuditMixin` (`src/core/audit.py`). The auth dependency sets the user in a `ContextVar`; never set `created_by` / `modified_by` manually and never pass the actor through use cases.
- Money is `Decimal` in Python and `NUMERIC` in Postgres. Never `float`.
- There are no migrations (`create_all`). Adding or changing a column on an existing table needs a manual `ALTER TABLE` or dropping the dev tables; tell the user. Alembic is on the roadmap, not installed in the flow.

## 6. Catalog values and constants

- Statuses, billing types and similar lookups are rows of the self-referencing `catalogs` table, fetched through `CatalogUseCases` (`require_item`, `default_item`).
- Rules compare by stable `code` with constants from `src/catalogs/domain/entities.py` (`BILLING_TYPE`, `HOURLY`, `FIXED`, `PROJECT_STATUS`, ...). Never compare by numeric id or display `name`, and never write a literal like `"HOURLY"` outside that module. Add a new constant there when a new code needs a rule.
- Names, order and active flag of catalog values are free to change; `code` is not.

## 7. Naming, language, typing

- English only: code, comments, docstrings, error messages, test names.
- snake_case for Python and for JSON fields (the API does not convert to camelCase). Classes in PascalCase; schemas `XCreate`, `XUpdate`, `XOut`; use case classes `XUseCases`; repositories `SQLXRepository` / `XRepository`.
- Type hints on all function parameters and returns. Use `X | None`, not `Optional[X]`.
- I/O is `async def` + `await` (asyncpg, aiosqlite in tests). Do not block the event loop.
- Imports at the top of the file (ruff organizes them). No unused imports, variables or commented-out code. No `print()`.

## 8. Tests

- `pytest` with `asyncio_mode = auto`. Three kinds: pure logic (`test_time_parsing.py`, `test_summary.py`), use cases with in-memory fakes (`tests/fakes.py`), and API tests through the real stack on a throwaway SQLite file (`test_api.py`).
- Each change adds or updates tests. A business rule gets a test that needs no database.
- Extend `tests/fakes.py` when a new port appears; do not mock SQLAlchemy.
- `tests/conftest.py` sets `SECRET_KEY` before importing `src`; keep that.

## 9. Security and secrets

- Passwords are hashed with Argon2 (`users/infrastructure/security.py`); tokens are JWT. Do not log tokens or passwords.
- Do not read, print or commit `.env`. Document new settings by key name in `README.md` and `core/config.py`.
- Registration is closed after the first user unless `ALLOW_REGISTRATION=true`.
- Image uploads are validated by content type in the use case (`ALLOWED_IMAGE_TYPES`, plus the size cap); files are served from `/uploads`.

## 10. What does NOT exist (do not assume it)

- No Alembic migrations, no frontend, no client report yet.
- No multi-user ownership (`owner_id`): every logged-in user sees every project.
- No Celery, Redis, GraphQL or second ORM.

## 11. Final sweep (before answering)

- [ ] `pytest` and `ruff check src tests` pass; `ruff format src tests` applied
- [ ] No dead code, unused imports, `print()`
- [ ] No hardcoded catalog ids or names; constants used
- [ ] `domain/` and `use_cases/` import nothing from FastAPI, Pydantic or SQLAlchemy
- [ ] New table has `AuditMixin`; new model module is imported in `main.py`
- [ ] README endpoint table updated if endpoints changed
