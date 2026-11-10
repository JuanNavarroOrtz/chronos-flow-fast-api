import pytest

from src.catalogs.domain.entities import BILLING_TYPE, PROJECT_STATUS
from src.core.errors import DuplicateError, InvalidDataError, NotFoundError
from tests.fakes import seeded_catalogs


async def test_seed_creates_catalogs_with_children_pointing_at_them():
    uc = await seeded_catalogs()
    roots = await uc.list_catalogs()
    assert [r.code for r in roots] == [BILLING_TYPE, PROJECT_STATUS, "TICKET_STATUS"]
    assert all(r.parent_id is None for r in roots)
    items = await uc.list_items(BILLING_TYPE)
    assert [i.code for i in items] == ["HOURLY", "FIXED"]
    assert all(i.parent_id == roots[0].id for i in items)


async def test_seeding_twice_does_not_duplicate():
    uc = await seeded_catalogs()
    await uc.seed_defaults()
    assert len(await uc.list_items(PROJECT_STATUS)) == 4


async def test_unknown_catalog_is_not_found():
    uc = await seeded_catalogs()
    with pytest.raises(NotFoundError):
        await uc.list_items("NOPE")


async def test_new_value_can_be_added_without_touching_code():
    uc = await seeded_catalogs()
    created = await uc.create_item(PROJECT_STATUS, "waiting", "Waiting for client", 5)
    assert created.code == "WAITING"
    assert (
        await uc.require_item(created.id, PROJECT_STATUS)
    ).name == "Waiting for client"
    with pytest.raises(DuplicateError):
        await uc.create_item(PROJECT_STATUS, "WAITING", "Again")


async def test_inactive_values_are_hidden_and_cannot_be_chosen():
    uc = await seeded_catalogs()
    cancelled = await uc.default_item(PROJECT_STATUS, "CANCELLED")
    await uc.update_item(PROJECT_STATUS, cancelled.id, is_active=False)
    assert "CANCELLED" not in [i.code for i in await uc.list_items(PROJECT_STATUS)]
    assert "CANCELLED" in [
        i.code for i in await uc.list_items(PROJECT_STATUS, only_active=False)
    ]
    with pytest.raises(InvalidDataError):
        await uc.require_item(cancelled.id, PROJECT_STATUS)


async def test_a_value_of_another_catalog_is_rejected():
    uc = await seeded_catalogs()
    hourly = await uc.default_item(BILLING_TYPE, "HOURLY")
    with pytest.raises(InvalidDataError):
        await uc.require_item(hourly.id, PROJECT_STATUS)
    with pytest.raises(
        NotFoundError
    ):  # and it can't be edited through the wrong catalog
        await uc.update_item(PROJECT_STATUS, hourly.id, name="x")
