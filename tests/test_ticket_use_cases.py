"""Use-case tests with in-memory fakes: no database, no disk, no web server.

This only works because the use case depends on interfaces (ports), not on SQLAlchemy.
"""

from types import SimpleNamespace

import pytest

from src.core.errors import (
    ConflictError,
    DuplicateError,
    InvalidDataError,
    NotFoundError,
)
from src.tickets.use_cases.ticket_use_cases import TicketUseCases
from tests.fakes import (
    FakeProjectRepo,
    FakeStorage,
    FakeTicketRepo,
    FakeUow,
    make_project,
    seeded_catalogs,
)


@pytest.fixture
async def env():
    repo, projects, uow, storage = (
        FakeTicketRepo(),
        FakeProjectRepo(),
        FakeUow(),
        FakeStorage(),
    )
    project = await projects.add(make_project("IC"))
    catalogs = await seeded_catalogs()
    uc = TicketUseCases(repo, projects, catalogs, uow, storage, max_image_bytes=100)
    return SimpleNamespace(uc=uc, repo=repo, uow=uow, storage=storage, project=project)


async def test_create_commits_and_rejects_duplicates(env):
    await env.uc.create(env.project.id, "IC-1", "First")
    assert env.uow.commits == 1
    with pytest.raises(DuplicateError):
        await env.uc.create(env.project.id, "ic-1", "Again")


async def test_ticket_code_must_start_with_the_project_acronym(env):
    with pytest.raises(InvalidDataError, match="IC-"):
        await env.uc.create(env.project.id, "XX-1", "Wrong prefix")


async def test_status_defaults_to_open_and_must_be_a_ticket_status(env):
    ticket = await env.uc.create(env.project.id, "IC-1", "First")
    assert ticket.status.code == "OPEN"
    with pytest.raises(InvalidDataError):
        await env.uc.create(
            env.project.id, "IC-2", "Bad status", status_id=1
        )  # a billing type


async def test_unknown_project_is_not_found(env):
    with pytest.raises(NotFoundError):
        await env.uc.create(999, "IC-1", "Orphan")


async def test_updating_the_code_keeps_the_prefix_rule(env):
    ticket = await env.uc.create(env.project.id, "IC-1", "First")
    with pytest.raises(InvalidDataError):
        await env.uc.update(ticket.id, code="XX-9")
    assert (await env.uc.update(ticket.id, code="ic-9")).code == "IC-9"


async def test_list_can_filter_by_project(env):
    other = await env.uc.create(env.project.id, "IC-1", "First")
    assert [t.id for t in await env.uc.list(env.project.id)] == [other.id]
    assert await env.uc.list(project_id=999) == []


async def test_add_image_stores_file_and_commits(env):
    ticket = await env.uc.create(env.project.id, "IC-1", "First")
    image = await env.uc.add_image(ticket.id, "a.png", "image/png", b"x")
    assert image.path in env.storage.files and env.uow.commits == 2


async def test_bad_type_or_size_never_touches_storage(env):
    ticket = await env.uc.create(env.project.id, "IC-1", "First")
    with pytest.raises(InvalidDataError):
        await env.uc.add_image(ticket.id, "a.txt", "text/plain", b"x")
    with pytest.raises(InvalidDataError):
        await env.uc.add_image(ticket.id, "big.png", "image/png", b"x" * 101)
    assert env.storage.files == set()


async def test_failed_db_write_removes_the_stored_file(env):
    ticket = await env.uc.create(env.project.id, "IC-1", "First")
    env.repo.fail_add_image = True
    with pytest.raises(RuntimeError):
        await env.uc.add_image(ticket.id, "a.png", "image/png", b"x")
    assert env.storage.files == set()  # no orphan


async def test_failed_commit_removes_the_stored_file(env):
    ticket = await env.uc.create(env.project.id, "IC-1", "First")
    env.uow.fail = True
    with pytest.raises(RuntimeError):
        await env.uc.add_image(ticket.id, "a.png", "image/png", b"x")
    assert env.storage.files == set()


async def test_delete_removes_the_files_after_commit(env):
    ticket = await env.uc.create(env.project.id, "IC-1", "First")
    await env.uc.add_image(ticket.id, "a.png", "image/png", b"x")
    await env.uc.delete(ticket.id)
    assert env.storage.files == set()


async def test_failed_commit_on_delete_keeps_the_files(env):
    ticket = await env.uc.create(env.project.id, "IC-1", "First")
    await env.uc.add_image(ticket.id, "a.png", "image/png", b"x")
    env.uow.fail = True  # the DB delete is rolled back, so the image must survive
    with pytest.raises(RuntimeError):
        await env.uc.delete(ticket.id)
    assert len(env.storage.files) == 1


async def test_remove_unknown_image_is_not_found(env):
    ticket = await env.uc.create(env.project.id, "IC-1", "First")
    with pytest.raises(NotFoundError):
        await env.uc.remove_image(ticket.id, 99)


def test_conflict_error_is_the_parent_of_duplicate():
    assert issubclass(DuplicateError, ConflictError)
