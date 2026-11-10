# Recipe: add a feature or endpoint

> Follow the steps in order. Rules referenced here live in `docs/conventions.md`; the architecture is in `README.md`.
> Example used below: a new entity `Widget` in a new feature folder `src/widgets/`.

## Step 0 - Before writing code

- [ ] Does the feature belong in an existing folder (`projects`, `tickets`, `time_logs`...)? Prefer extending it.
- [ ] Does it need a catalog value (a status or type)? Add the constants to `src/catalogs/domain/entities.py` and the default rows to `src/catalogs/domain/seed.py`.

## Step 1 - Domain (pure Python)

`src/widgets/domain/entities.py`: the entity with its business rules. No FastAPI, Pydantic or SQLAlchemy.

```python
from dataclasses import dataclass

from src.core.errors import InvalidDataError


@dataclass
class WidgetEntity:
    name: str
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidDataError("name cannot be empty")
```

`src/widgets/domain/repositories.py`: the port.

```python
from typing import Protocol

from src.widgets.domain.entities import WidgetEntity


class WidgetRepository(Protocol):
    async def add(self, widget: WidgetEntity) -> WidgetEntity: ...
    async def get(self, widget_id: int) -> WidgetEntity | None: ...
    async def list(self) -> list[WidgetEntity]: ...
```

## Step 2 - Use cases (pure Python)

`src/widgets/use_cases/widget_use_cases.py`: one class, constructor receives the repository and `UnitOfWork`.

```python
from src.core.errors import NotFoundError
from src.core.unit_of_work import UnitOfWork
from src.widgets.domain.entities import WidgetEntity
from src.widgets.domain.repositories import WidgetRepository


class WidgetUseCases:
    def __init__(self, repo: WidgetRepository, uow: UnitOfWork) -> None:
        self._repo = repo
        self._uow = uow

    async def create(self, name: str) -> WidgetEntity:
        created = await self._repo.add(WidgetEntity(name=name))
        await self._uow.commit()
        return created

    async def get(self, widget_id: int) -> WidgetEntity:
        widget = await self._repo.get(widget_id)
        if widget is None:
            raise NotFoundError(f"Widget {widget_id} not found")
        return widget
```

Rules: raise `DomainError` subclasses, commit once, no HTTP.

## Step 3 - Tests first (no database)

Add `FakeWidgetRepo` to `tests/fakes.py` and write `tests/test_widgets.py` running `WidgetUseCases` against it (see `tests/test_ticket_use_cases.py`). Cover the happy path and each rule that raises an error.

## Step 4 - Infrastructure

1. `infrastructure/models.py`: SQLAlchemy model `class WidgetModel(AuditMixin, Base)` with an explicit `__tablename__`; money as `Numeric`.
2. `infrastructure/schemas.py`: `WidgetCreate`, `WidgetUpdate` (optional fields), `WidgetOut` with `from_entity`.
3. `infrastructure/repositories.py`: `SQLWidgetRepository` implementing the port; map entity <-> model; only `flush`.
4. `infrastructure/router.py`: `get_widget_use_cases` dependency, `router = APIRouter(prefix="/widgets", tags=["widgets"])`, thin routes (see conventions section 2). PATCH uses `body.model_dump(exclude_unset=True)`.

## Step 5 - Register in `src/main.py`

- Import the models module so `create_all` sees the table: `from src.widgets.infrastructure import models as _widget_models  # noqa: F401  (register tables)`.
- `app.include_router(widgets_router, dependencies=_protected)`.
- If a new `DomainError` type was added, add it to `_STATUS`.

## Step 6 - API test and docs

- Add API tests in `tests/test_api.py` style (real stack, throwaway SQLite): create, read, validation error, 404, requires token.
- Update the endpoint table in `README.md` section 2.
- Remember: there are no migrations. If you changed a table that already exists in the dev database, tell the user to drop it or run the `ALTER TABLE`.

## Step 7 - Final sweep

Run the checklist in `docs/conventions.md` section 11.
