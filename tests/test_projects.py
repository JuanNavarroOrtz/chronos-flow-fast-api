from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.catalogs.domain.entities import BILLING_TYPE, FIXED, HOURLY, PROJECT_STATUS
from src.core.errors import (
    ConflictError,
    DuplicateError,
    InvalidDataError,
    NotFoundError,
)
from src.projects.use_cases.project_use_cases import ProjectUseCases
from tests.fakes import (
    FIXED_ITEM,
    FakeProjectRepo,
    FakeUow,
    make_project,
    seeded_catalogs,
)

# ---- entity rules (pure, no fakes needed) -------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"hourly_rate": None},  # hourly without a rate
        {"hourly_rate": Decimal(0)},
        {"fixed_price": Decimal(500)},  # hourly with a fixed price
        {"billing_type": FIXED_ITEM, "hourly_rate": None},  # fixed without a price
        {
            "billing_type": FIXED_ITEM,
            "fixed_price": Decimal(500),
        },  # fixed with an hourly rate
        {"end_date": date(2026, 6, 1)},  # ends before it starts
        {"name": "   "},
        {"acronym": ""},
        {"acronym": "I"},
        {"acronym": "1AB"},
        {"acronym": "I C"},
        {"acronym": "TOOLONGACRONYM"},
    ],
)
def test_invalid_projects_are_rejected(overrides):
    with pytest.raises(InvalidDataError):
        make_project(**overrides)


def test_valid_fixed_price_project_has_no_task_rate():
    project = make_project(
        "AB",
        billing_type=FIXED_ITEM,
        hourly_rate=None,
        fixed_price=Decimal(5000),
    )
    assert project.task_hourly_rate is None


def test_hourly_project_hands_its_rate_to_tasks():
    assert make_project().task_hourly_rate == Decimal("7.00")


# ---- use cases (with fakes) ---------------------------------------------------------------


@pytest.fixture
async def env():
    repo, uow, catalogs = FakeProjectRepo(), FakeUow(), await seeded_catalogs()
    ids = SimpleNamespace(
        hourly=(await catalogs.default_item(BILLING_TYPE, HOURLY)).id,
        fixed=(await catalogs.default_item(BILLING_TYPE, FIXED)).id,
        active=(await catalogs.default_item(PROJECT_STATUS, "ACTIVE")).id,
        on_hold=(await catalogs.default_item(PROJECT_STATUS, "ON_HOLD")).id,
    )
    uc = ProjectUseCases(repo, uow, catalogs)
    return SimpleNamespace(uc=uc, repo=repo, uow=uow, ids=ids)


async def _create(env, **overrides):
    args = {
        "name": "iCargo",
        "acronym": "ic",
        "billing_type_id": env.ids.hourly,
        "start_date": date(2026, 7, 1),
        "hourly_rate": Decimal(7),
    } | overrides
    return await env.uc.create(**args)


async def test_create_defaults_the_status_to_active(env):
    project = await _create(env)
    assert project.acronym == "IC"
    assert project.status.code == "ACTIVE" and project.billing_type.code == HOURLY
    assert env.uow.commits == 1


async def test_unknown_or_wrong_catalog_ids_are_rejected(env):
    with pytest.raises(InvalidDataError):
        await _create(env, billing_type_id=999)
    # a status id is not a valid billing type, even though the row exists
    with pytest.raises(InvalidDataError):
        await _create(env, billing_type_id=env.ids.active)
    with pytest.raises(InvalidDataError):
        await _create(env, status_id=env.ids.hourly)


async def test_duplicate_acronym_is_rejected(env):
    await _create(env)
    with pytest.raises(DuplicateError):
        await _create(env, name="Other")


async def test_update_changes_fields_and_status(env):
    project = await _create(env)
    updated = await env.uc.update(
        project.id, {"name": "iCargo v2", "status_id": env.ids.on_hold}
    )
    assert updated.name == "iCargo v2" and updated.status.code == "ON_HOLD"


async def test_switching_to_fixed_price_drops_the_hourly_rate(env):
    project = await _create(env)
    updated = await env.uc.update(
        project.id, {"billing_type_id": env.ids.fixed, "fixed_price": Decimal(5000)}
    )
    assert updated.billing_type.code == FIXED
    assert updated.hourly_rate is None and updated.fixed_price == Decimal("5000.00")


async def test_switching_to_fixed_price_needs_a_price(env):
    project = await _create(env)
    with pytest.raises(InvalidDataError):
        await env.uc.update(project.id, {"billing_type_id": env.ids.fixed})


async def test_required_fields_cannot_be_cleared(env):
    project = await _create(env)
    with pytest.raises(InvalidDataError):
        await env.uc.update(project.id, {"name": None})
    with pytest.raises(InvalidDataError):
        await env.uc.update(project.id, {"status_id": None})


async def test_end_date_can_be_cleared(env):
    project = await _create(env, end_date=date(2026, 12, 31))
    assert (await env.uc.update(project.id, {"end_date": None})).end_date is None


async def test_acronym_cannot_change_once_tickets_use_it(env):
    project = await _create(env)
    env.repo.ticket_counts[project.id] = 1
    with pytest.raises(ConflictError):
        await env.uc.update(project.id, {"acronym": "XY"})
    env.repo.ticket_counts[project.id] = 0
    assert (await env.uc.update(project.id, {"acronym": "xy"})).acronym == "XY"


async def test_delete_is_blocked_while_it_has_tickets(env):
    project = await _create(env)
    env.repo.ticket_counts[project.id] = 2
    with pytest.raises(ConflictError, match="2 ticket"):
        await env.uc.delete(project.id)
    env.repo.ticket_counts[project.id] = 0
    await env.uc.delete(project.id)
    with pytest.raises(NotFoundError):
        await env.uc.get(project.id)
