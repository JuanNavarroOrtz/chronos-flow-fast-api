# Chronos Flow

A small personal website to **register tickets and the tasks done on each ticket**, in one standard
format, so I no longer build a custom Excel sheet for every client.

The data has one fixed structure: **Project -> Ticket -> Task**.

- **Project**: name, acronym (`IC`), start/end date, status, how the client pays (per hour or a fixed
  price for the whole project), plus who created/modified it and when.
- **Ticket** (under a project): code = project acronym + number (`IC-6`), title, description, screenshots/images, status.
- **Task** (under a ticket): date, time range, hours, what was done. Hours and payout are calculated, not typed by hand.
- **Summary**: totals and per-ticket breakdown computed from the data (what the spreadsheet formulas did).
- **Final report for the client** (planned): generated from the same data, always in the same format.

Because the data is entered once in a fixed format, reports for different clients come from the same
source instead of being rebuilt in a new spreadsheet each time.

This is also a **learning project**: FastAPI with a Clean Architecture layout. Sections 4-8 explain the
patterns and map them to DRF.

---

## 1. Run it

From the project folder, in PowerShell:

```powershell
venv\Scripts\activate
pip install -r requirements.txt     # only needed if you recreate the venv
uvicorn src.main:app --reload
```

- Interactive docs (try every endpoint in the browser): http://127.0.0.1:8000/docs
- The database is **PostgreSQL**. Create an empty database first (`CREATE DATABASE chronos_flow;`); the app creates
  the tables on first run. The `uploads/` folder is also created on first run.
- Settings live in `.env`: `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `UPLOAD_DIR`, plus
  `SECRET_KEY` (signs the login tokens, required), `ACCESS_TOKEN_MINUTES` and `ALLOW_REGISTRATION`.
- **Login first.** The very first `POST /auth/register` always works (that is your account); after that
  registration is closed unless `ALLOW_REGISTRATION=true`. In `/docs`, click **Authorize** and enter your email as the
  username. Every endpoint except `/auth/*` needs the token.
- There are no migrations. `create_all` only creates missing tables, it never alters existing ones. If you change a
  model after the tables exist, drop the dev tables (or run the `ALTER TABLE` by hand) and restart.
- The tests still use a throwaway SQLite file, so they need no Postgres.
- Start order in the API: create a **project** first, then tickets in it, then tasks on the tickets.

Run the tests and the linter:

```powershell
pytest
ruff check src tests
ruff format src tests
```

## 2. Endpoints

| Method | URL | What it does |
|---|---|---|
| POST | `/auth/register` | Create the first user (later ones only if `ALLOW_REGISTRATION=true`) |
| POST | `/auth/login` | Form fields `username` (your email) + `password`, returns a bearer token |
| GET | `/users/me` | The logged-in user |
| GET | `/catalogs` | The catalogs: `BILLING_TYPE`, `PROJECT_STATUS`, `TICKET_STATUS` |
| GET / POST | `/catalogs/{code}/items` | List / add the values of a catalog (`?include_inactive=true`) |
| PATCH | `/catalogs/{code}/items/{id}` | Rename, reorder or deactivate a value (its `code` never changes) |
| POST | `/projects` | Create a project, see "Projects" below |
| GET | `/projects`, `/projects/{id}` | List / read projects |
| PATCH | `/projects/{id}` | Edit a project |
| DELETE | `/projects/{id}` | Delete a project (409 while it still has tickets) |
| POST | `/tickets` | Create a ticket `{project_id, code: "IC-6", title, description, status_id}` |
| GET | `/tickets`, `/tickets/{id}` | List / read tickets with their images (`/tickets?project_id=1` to filter) |
| PATCH | `/tickets/{id}` | Edit title, description, status or code |
| DELETE | `/tickets/{id}` | Delete ticket + its tasks + image files |
| POST | `/tickets/{id}/images` | Upload an image (form field `file`) |
| DELETE | `/tickets/{id}/images/{image_id}` | Remove an image |
| POST | `/tickets/{id}/tasks` | Log a task: `work_date` + (`time_text` or `hours`) + `description` |
| GET | `/tickets/{id}/tasks` | List a ticket's tasks |
| PATCH / DELETE | `/tasks/{task_id}` | Edit / delete a task |
| GET | `/analytics/summary` | KPIs + per-ticket table (`?date_from=&date_to=&project_id=` all optional) |

**Projects.** Fields: `name`, `acronym` (2-10 letters/digits, e.g. `IC`, unique), `start_date`, `end_date` (optional),
`status_id` and `billing_type_id`. Both are ids of **catalog** values: ask `GET /catalogs/PROJECT_STATUS/items`
and `GET /catalogs/BILLING_TYPE/items` to fill your dropdowns (status defaults to `ACTIVE`). The billing type decides
which price you must send:

| Billing type (code) | You must send | What the client pays |
|---|---|---|
| `HOURLY` | `hourly_rate` | `hourly_rate` x hours worked |
| `FIXED` | `fixed_price` | `fixed_price` once, for the whole project |

Every table also has `created_at`, `created_by`, `modified_at`, `modified_by` (the user ids), filled in
automatically. Rules: the acronym can't change
once tickets use it (ticket codes start with it), and a project with tickets can't be deleted.
Switching a project from `HOURLY` to `FIXED` (or back) clears the old price automatically.

**How hours and payout work.** Send `time_text` like `"7:05 PM TO 9:56 PM"` (also `-`, several ranges
separated by commas, ranges crossing midnight) and hours are computed: `2.85`. Send `hours` yourself
and that value wins (for the rows where your log differs from the clock).
- On an `HOURLY` project, each task's payout = hours x the project's rate. The rate is copied onto the task when it is
  logged, so changing the project's rate later does not rewrite old tasks.
- On a `FIXED` project, tasks have no payout (`null`); the summary counts the project's fixed price once, however
  many tasks it has. (If you filter the summary by date, the price is counted when the project has tasks in that range.)

## 3. Project map

```
src/
  core/            shared kernel: settings, DB engine/session, errors, Unit of Work, audit columns
  users/           login: users table, password hashing (Argon2), JWT tokens, who is the current user
  catalogs/        lookup values (billing types, statuses) in one self-referencing table
  projects/        feature 1: projects (billing mode, dates, audit fields)
    domain/          entities + repository interface   (pure Python)
    use_cases/       the operations the app can do     (pure Python)
    infrastructure/  everything that touches the outside world: SQLAlchemy, FastAPI, files
  tickets/         feature 2: tickets of a project (title, description, images, status)
  time_logs/       feature 3: the tasks of a ticket, with hours
  analytics/       feature 4: summary numbers; the client report will build on this
  main.py          builds the app, registers routers, maps errors to HTTP codes
tests/             pure-logic tests, use-case tests with fakes, API tests through the real stack
```

### Catalogs and `parent_id`

All lookup values live in **one table**, `catalogs`. A row with `parent_id = NULL` is a catalog; the rows that point at
it with `parent_id` are its values:

```
id  parent_id  code            name
1   NULL       BILLING_TYPE    Billing type
2   1          HOURLY          Per hour
3   1          FIXED           Fixed price
4   NULL       PROJECT_STATUS  Project status
5   4          ACTIVE          Active
...
```

`projects.billing_type_id`, `projects.status_id` and `tickets.status_id` are real foreign keys to this table. Adding a
status is a `POST /catalogs/PROJECT_STATUS/items`, no code change. The default rows are inserted on startup if they
are missing. One thing stays in code: the *rules* for a billing type (hourly needs a rate, fixed needs a price) look at
the stable `code`, so `HOURLY` and `FIXED` must keep existing. Names, order and active flag are free to change.

### Audit columns

`AuditMixin` ([src/core/audit.py](src/core/audit.py)) adds `created_at`, `created_by`, `modified_at`, `modified_by` to
every table. The auth dependency stores the logged-in user id in a `ContextVar` for the request, and SQLAlchemy fills
the columns on insert/update, so use cases never pass an "actor" around. `NULL` means "no user" (seed data).

## 4. The core idea: the dependency rule

```
   infrastructure  ──►  use_cases  ──►  domain
   (FastAPI, SQLAlchemy)   (what the app does)   (business rules)

   arrows = "is allowed to import". Never the other way around.
```

- `domain/` and `use_cases/` **never import** FastAPI, Pydantic or SQLAlchemy.
- Only `infrastructure/` knows about HTTP and the database.

**Why bother?** You can test the business rules (parsing times, computing payout, the KPIs) with plain
`pytest` functions, no server and no database. See `tests/test_time_parsing.py` and
`tests/test_summary.py`: they run in milliseconds. And you could swap Postgres for another database, or FastAPI for
something else, without touching the rules.

## 5. The patterns, and where to find each one

| Pattern | What it means | Where |
|---|---|---|
| **Feature-first modules** | Group code by feature (`tickets/`), not by type (`models/`, `views/`) | the three top-level folders |
| **Entity** | A plain Python object holding business rules, no DB knowledge | [src/tickets/domain/entities.py](src/tickets/domain/entities.py), [src/time_logs/domain/entities.py](src/time_logs/domain/entities.py) |
| **ORM model** | The database table mapping. Separate from the entity | `infrastructure/models.py` |
| **DTO / schema** | The shape of request and response JSON (Pydantic) | `infrastructure/schemas.py` |
| **Repository** | An object that hides *how* data is stored behind methods like `add`, `get`, `list` | interface: `domain/repositories.py`, implementation: `infrastructure/repositories.py` |
| **Port & adapter** | The interface (`Protocol`) is the *port*; the SQL class is the *adapter* | same files as above |
| **Use case** | One class holding the app's operations (create ticket, log task...) | `use_cases/ticket_use_cases.py`, `use_cases/task_use_cases.py` |
| **Dependency injection** | Objects receive what they need instead of creating it | `Depends(...)` in `dependencies.py` / `router.py` |
| **Unit of Work** | Repositories only *stage* changes (`flush`); the use case calls `uow.commit()` once, so a multi-step operation is all-or-nothing | [src/core/unit_of_work.py](src/core/unit_of_work.py), `SQLUnitOfWork` in [src/core/database.py](src/core/database.py) |
| **Storage port** | File storage is an interface too, so the *use case* owns the "save file, then DB row" flow and cleans up on failure | [src/tickets/domain/storage.py](src/tickets/domain/storage.py), adapter: `infrastructure/storage.py` |
| **Pure function** | Same input gives same output, no I/O: easiest thing to test | [src/analytics/use_cases/summary.py](src/analytics/use_cases/summary.py) |
| **Test with fakes** | Because use cases depend on ports, tests swap in in-memory fakes: no DB, no disk | [tests/test_ticket_use_cases.py](tests/test_ticket_use_cases.py) |
| **Domain errors mapped at the edge** | Rules raise `NotFoundError`; only `main.py` turns that into HTTP 404 | [src/core/errors.py](src/core/errors.py), [src/main.py](src/main.py) |

## 6. Follow one request through the layers

`POST /tickets/3/tasks` with `{"work_date": "2026-07-27", "time_text": "8:20 PM - 10:20 PM"}`:

1. **Router** ([src/time_logs/infrastructure/router.py](src/time_logs/infrastructure/router.py)): FastAPI validates the body
   against `TaskCreate` (schema). Bad types are rejected here with a 422.
2. **Dependency injection**: `get_task_use_cases` builds a `TaskUseCases`, handing it the SQL repositories,
   the DB session and the hourly rate. FastAPI calls it because the route declares `uc: UseCases`.
3. **Use case** (`TaskUseCases.log`): checks the ticket exists (via the ticket repository), then calls the domain.
4. **Domain** (`resolve_hours` + `time_parsing.py`): turns the text into `Decimal("2.00")`. Builds a `TaskEntity`.
   Invalid text raises `InvalidDataError`.
5. **Repository** (`SQLTaskRepository.add`): converts the entity into a `TaskModel`, flushes (to get the id), converts back.
6. **Unit of Work**: the use case calls `uow.commit()`. If anything fails before this line, the session closes and the transaction rolls back.
7. **Router again**: `TaskOut.from_entity` shapes the response, including the computed `payout`.
8. If anything raised a domain error, [src/main.py](src/main.py) turns it into a 404 / 409 / 422 JSON response.

## 7. Coming from DRF: the translation table

| DRF | This project | Note |
|---|---|---|
| `models.Model` | `infrastructure/models.py` (SQLAlchemy) | Explicit session; there is no `Model.objects` |
| `Serializer` | Pydantic classes in `schemas.py` | Validate input *and* shape output; types come from annotations |
| `ViewSet` / `APIView` | Functions in `router.py` | One function per endpoint; `APIRouter` ~ `DefaultRouter` |
| `urls.py` | `include_router(...)` in `main.py` | Paths are declared on the decorators |
| `permission_classes`, `get_queryset()` | `Depends(...)` | Dependencies are injected into the function signature |
| `settings.py` | `core/config.py` (`BaseSettings`) | Reads `.env` and validates types |
| `makemigrations` / `migrate` | Alembic (not set up yet) | For now tables are created on startup |
| `ValidationError` -> 400 | `DomainError` -> handler in `main.py` | You choose the mapping |
| browsable API | `/docs` (Swagger), automatic | Generated from your type hints |
| `Model.save()` / fat models | Entity + use case + repository | The big difference, see below |

**The honest trade-off.** In DRF, a `ModelSerializer` + `ModelViewSet` gives you model, validation,
persistence and endpoint in about 10 lines. Here the same feature spreads across entity, model,
schema, repository, use case and router. That is **more code**, in exchange for isolation and
testability. For a small CRUD app DRF's shortcut is often the better choice; this layout pays off when
business rules grow. The point of this project is to feel both sides of that trade.

FastAPI-specific things worth knowing:
- `async def` everywhere: the DB driver (`asyncpg`) is async, so every DB call uses `await`.
- Type hints are the framework: `ticket_id: int` in a route both parses and documents the parameter.
- `Annotated[X, Depends(f)]` means "call `f` and pass me the result".

## 8. Exercises to learn by doing

1. **Add a field.** Add `estimate_hours` to tickets. Touch, in order: entity, model, schema, repository mapper. Notice how much each layer owns.
2. **Add a rule.** Reject a task whose `work_date` is in the future, in the *domain* layer, then write a test that needs no database.
3. **Add a use case.** "Close ticket": sets status `CLOSED`, refuses if it has no tasks. Where does the "has tasks" check live?
4. **Swap the storage.** Write an `InMemoryTicketRepository` (a dict) that satisfies `TicketRepository` and run `TicketUseCases` with it in a test. That is the payoff of the repository pattern.
5. **Add Alembic.** `alembic init`, point it at `Base.metadata`, replace `create_all` in `main.py`.

## 9. Known trade-offs (on purpose)

- `tickets` imports `ProjectRepository` (to check the project and its acronym) and `time_logs` imports `TicketRepository` and `ProjectRepository` (to find the rate). They go through interfaces, but the features are coupled. A stricter version gives each feature its own tiny lookup port.
- Audit columns are filled through a `ContextVar` set by the auth dependency. It is less explicit than passing the user
  into each use case, but it keeps every use case free of "who is acting". Anything that writes outside a request
  (a script, the startup seed) leaves `created_by` empty.
- There is one tenant: every logged-in user sees every project (no `owner_id` yet). Fine while you are the only user.
- `/uploads/...` image URLs are public static files; only the API endpoints need the token.
- Entities hold catalog values as small `CatalogItem(id, code, name)` objects, so `projects`, `tickets` import from `catalogs`.
- Entities are fairly thin (rules live in use cases and small functions). That is a simplification of "rich domain model" DDD.
- The upload is read fully into memory before the size check (fine at a 10 MB cap).
- Money is `Decimal` in Python and `NUMERIC` in Postgres, so it stays exact.

## 10. Roadmap

The goal is: register everything in the website, then hand the client a report in the standard format.

- [x] API: projects, tickets, images, tasks, hours calculation, summary
- [x] Users + login (JWT), catalogs with `parent_id`, audit columns on every table
- [ ] Per-user data (`owner_id`) if more than one person will ever log in
- [ ] **Web UI** (the actual website): create a ticket with images, add tasks under it, see hours and payout
- [ ] **Client report**: pick a client/date range, get the final report (PDF and/or Excel) in the standard format
- [ ] Import script for the existing spreadsheet (71 rows), to check totals: 174.99 h, $1,224.93
- [ ] Client name on the project, so reports can be grouped per client (not decided yet)
- [ ] Alembic migrations
