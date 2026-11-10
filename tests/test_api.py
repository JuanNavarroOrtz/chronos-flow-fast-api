import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.catalogs.infrastructure.repositories import SQLCatalogRepository
from src.catalogs.use_cases.catalog_use_cases import CatalogUseCases
from src.core.config import settings
from src.core.database import Base, SQLUnitOfWork, get_db
from src.main import app

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'test.db'}", poolclass=NullPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await CatalogUseCases(
            SQLCatalogRepository(session), SQLUnitOfWork(session)
        ).seed_defaults()

    async def override():
        async with factory() as session:
            await session.execute(text("PRAGMA foreign_keys=ON"))
            yield session

    app.dependency_overrides[get_db] = override
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        await sign_in(c)
        yield c
    app.dependency_overrides.clear()
    await engine.dispose()


async def sign_in(client, email="me@example.com", password="secret-pass") -> dict:
    """Creates the first user, logs in, and makes the client send the token from now on."""
    r = await client.post(
        "/auth/register",
        json={"email": email, "full_name": "Me", "password": password},
    )
    assert r.status_code == 201, r.text
    login = await client.post(
        "/auth/login", data={"username": email, "password": password}
    )
    assert login.status_code == 200, login.text
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    return r.json()


async def item_id(client, catalog, code) -> int:
    items = (await client.get(f"/catalogs/{catalog}/items")).json()
    return next(i["id"] for i in items if i["code"] == code)


async def make_project(client, **overrides) -> dict:
    body = {
        "name": "iCargo",
        "acronym": "IC",
        "billing_type_id": await item_id(client, "BILLING_TYPE", "HOURLY"),
        "hourly_rate": "7.00",
        "start_date": "2026-07-01",
    } | overrides
    r = await client.post("/projects", json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def make_ticket(client, project_id, code="IC-1", title="A") -> dict:
    r = await client.post(
        "/tickets", json={"project_id": project_id, "code": code, "title": title}
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---- projects ------------------------------------------------------------------------------


async def test_project_crud_and_audit_fields(client):
    me = (await client.get("/users/me")).json()
    p = await make_project(client, acronym="ic", end_date="2026-12-31")
    assert p["acronym"] == "IC" and p["hourly_rate"] == 7.0
    assert p["status"]["code"] == "ACTIVE" and p["billing_type"]["code"] == "HOURLY"
    assert p["fixed_price"] is None
    assert p["created_by"] == p["modified_by"] == me["id"]

    on_hold = await item_id(client, "PROJECT_STATUS", "ON_HOLD")
    patched = await client.patch(
        f"/projects/{p['id']}", json={"name": "iCargo 2", "status_id": on_hold}
    )
    assert patched.json()["name"] == "iCargo 2"
    assert patched.json()["status"]["code"] == "ON_HOLD"
    assert patched.json()["modified_at"] >= p["modified_at"]
    assert patched.json()["created_at"] == p["created_at"]

    assert (await client.get(f"/projects/{p['id']}")).json()["name"] == "iCargo 2"
    assert [x["id"] for x in (await client.get("/projects")).json()] == [p["id"]]
    assert (await client.get("/projects/999")).status_code == 404


async def test_project_validation_and_conflicts(client):
    p = await make_project(client)
    hourly = await item_id(client, "BILLING_TYPE", "HOURLY")
    fixed = await item_id(client, "BILLING_TYPE", "FIXED")
    base = {"name": "X", "acronym": "XY", "start_date": "2026-07-01"}

    no_rate = {**base, "billing_type_id": hourly}
    assert (await client.post("/projects", json=no_rate)).status_code == 422
    no_price = {**base, "billing_type_id": fixed}
    assert (await client.post("/projects", json=no_price)).status_code == 422
    backwards = {
        **base,
        "billing_type_id": hourly,
        "hourly_rate": 5,
        "end_date": "2026-01-01",
    }
    assert (await client.post("/projects", json=backwards)).status_code == 422
    nope = {**base, "billing_type_id": 9999, "hourly_rate": 5}
    assert (await client.post("/projects", json=nope)).status_code == 422
    a_status_is_not_a_billing_type = {
        **base,
        "billing_type_id": await item_id(client, "PROJECT_STATUS", "ACTIVE"),
        "hourly_rate": 5,
    }
    assert (
        await client.post("/projects", json=a_status_is_not_a_billing_type)
    ).status_code == 422

    dup = {**base, "acronym": "IC", "billing_type_id": hourly, "hourly_rate": 5}
    assert (await client.post("/projects", json=dup)).status_code == 409

    await make_ticket(client, p["id"])
    assert (
        await client.patch(f"/projects/{p['id']}", json={"acronym": "ZZ"})
    ).status_code == 409
    assert (
        await client.delete(f"/projects/{p['id']}")
    ).status_code == 409  # still has a ticket


async def test_switch_project_to_fixed_price_and_delete_empty_project(client):
    p = await make_project(client)
    fixed = await item_id(client, "BILLING_TYPE", "FIXED")
    r = await client.patch(
        f"/projects/{p['id']}", json={"billing_type_id": fixed, "fixed_price": "5000"}
    )
    assert r.json()["billing_type"]["code"] == "FIXED"
    assert r.json()["fixed_price"] == 5000.0 and r.json()["hourly_rate"] is None
    assert (await client.delete(f"/projects/{p['id']}")).status_code == 204
    assert (await client.get(f"/projects/{p['id']}")).status_code == 404


# ---- tickets, images, tasks, summary --------------------------------------------------------


async def test_ticket_with_image_tasks_and_summary(client, tmp_path):
    project = await make_project(client)
    r = await client.post(
        "/tickets",
        json={
            "project_id": project["id"],
            "code": "ic-6",
            "title": "Cargo",
            "description": "FOB/CIF",
        },
    )
    assert r.status_code == 201 and r.json()["code"] == "IC-6"
    assert r.json()["project_id"] == project["id"]
    assert r.json()["status"]["code"] == "OPEN" and r.json()["created_by"] is not None
    tid = r.json()["id"]

    dup = {"project_id": project["id"], "code": "IC-6", "title": "dup"}
    assert (await client.post("/tickets", json=dup)).status_code == 409
    wrong_prefix = {"project_id": project["id"], "code": "XX-1", "title": "x"}
    assert (await client.post("/tickets", json=wrong_prefix)).status_code == 422
    unknown_project = {"project_id": 999, "code": "IC-1", "title": "x"}
    assert (await client.post("/tickets", json=unknown_project)).status_code == 404

    up = await client.post(
        f"/tickets/{tid}/images", files={"file": ("shot.png", PNG, "image/png")}
    )
    assert up.status_code == 201 and up.json()["url"].startswith("/uploads/")
    assert len(list((tmp_path / "uploads").rglob("*.png"))) == 1
    bad = await client.post(
        f"/tickets/{tid}/images", files={"file": ("x.txt", b"hi", "text/plain")}
    )
    assert bad.status_code == 422

    t1 = await client.post(
        f"/tickets/{tid}/tasks",
        json={
            "work_date": "2026-07-27",
            "time_text": "8:20 PM - 10:20 PM",
            "description": "Fix",
        },
    )
    assert t1.status_code == 201 and t1.json()["hours"] == 2.0
    assert (
        t1.json()["hourly_rate"] == 7.0 and t1.json()["payout"] == 14.0
    )  # rate from the project
    t2 = await client.post(
        f"/tickets/{tid}/tasks", json={"work_date": "2026-07-28", "hours": "1.5"}
    )
    assert t2.json()["payout"] == 10.5
    assert (
        await client.post(f"/tickets/{tid}/tasks", json={"work_date": "2026-07-28"})
    ).status_code == 422
    unknown = await client.post(
        "/tickets/999/tasks", json={"work_date": "2026-07-28", "hours": 1}
    )
    assert unknown.status_code == 404

    patched = await client.patch(
        f"/tasks/{t2.json()['id']}", json={"time_text": "9:00 AM TO 10:00 AM"}
    )
    assert patched.json()["hours"] == 1.0

    s = (await client.get("/analytics/summary")).json()
    assert s["total_hours"] == 3.0 and s["total_payout"] == 21.0
    assert s["tickets"][0]["code"] == "IC-6" and s["tickets"][0]["percentage"] == 100.0

    assert (await client.delete(f"/tickets/{tid}")).status_code == 204
    assert (await client.get("/analytics/summary")).json()[
        "total_tasks"
    ] == 0  # tasks cascaded
    assert list((tmp_path / "uploads").rglob("*.png")) == []  # files removed too


async def test_changing_the_project_rate_does_not_rewrite_old_tasks(client):
    project = await make_project(client)
    tid = (await make_ticket(client, project["id"]))["id"]
    old = (
        await client.post(
            f"/tickets/{tid}/tasks", json={"work_date": "2026-08-01", "hours": 2}
        )
    ).json()
    await client.patch(f"/projects/{project['id']}", json={"hourly_rate": "10"})
    new = (
        await client.post(
            f"/tickets/{tid}/tasks", json={"work_date": "2026-08-02", "hours": 2}
        )
    ).json()
    assert old["payout"] == 14.0 and new["payout"] == 20.0


async def test_fixed_price_project_has_no_task_payout_and_counts_once(client):
    fixed = await make_project(
        client,
        name="Web",
        acronym="WB",
        billing_type_id=await item_id(client, "BILLING_TYPE", "FIXED"),
        hourly_rate=None,
        fixed_price="1000",
    )
    hourly = await make_project(client)
    t_fixed = (await make_ticket(client, fixed["id"], "WB-1"))["id"]
    t_hourly = (await make_ticket(client, hourly["id"], "IC-1"))["id"]

    a = (
        await client.post(
            f"/tickets/{t_fixed}/tasks", json={"work_date": "2026-08-01", "hours": 2}
        )
    ).json()
    await client.post(
        f"/tickets/{t_fixed}/tasks", json={"work_date": "2026-08-02", "hours": 3}
    )
    await client.post(
        f"/tickets/{t_hourly}/tasks", json={"work_date": "2026-08-02", "hours": 1}
    )
    assert a["hourly_rate"] is None and a["payout"] is None

    everything = (await client.get("/analytics/summary")).json()
    assert (
        everything["total_hours"] == 6.0 and everything["total_payout"] == 1007.0
    )  # 1000 once + 1h x 7
    only_fixed = (
        await client.get(f"/analytics/summary?project_id={fixed['id']}")
    ).json()
    assert only_fixed["total_hours"] == 5.0 and only_fixed["total_payout"] == 1000.0
    assert (await client.get("/analytics/summary?project_id=999")).json()[
        "total_tasks"
    ] == 0

    by_project = (await client.get(f"/tickets?project_id={fixed['id']}")).json()
    assert [t["code"] for t in by_project] == ["WB-1"]


async def test_edit_ticket_and_delete_image_and_task(client, tmp_path):
    project = await make_project(client)
    tid = (await make_ticket(client, project["id"], "IC-1"))["id"]
    await make_ticket(client, project["id"], "IC-2", "B")

    closed = await item_id(client, "TICKET_STATUS", "CLOSED")
    patched = await client.patch(
        f"/tickets/{tid}", json={"title": "A2", "status_id": closed}
    )
    assert patched.json()["title"] == "A2"
    assert patched.json()["status"]["code"] == "CLOSED"
    assert (
        await client.patch(f"/tickets/{tid}", json={"code": "IC-2"})
    ).status_code == 409
    assert (
        await client.patch(f"/tickets/{tid}", json={"code": "nope"})
    ).status_code == 422
    assert (
        await client.patch(f"/tickets/{tid}", json={"code": "XX-1"})
    ).status_code == 422

    img = (
        await client.post(
            f"/tickets/{tid}/images", files={"file": ("a.png", PNG, "image/png")}
        )
    ).json()
    assert (
        await client.delete(f"/tickets/{tid}/images/{img['id']}")
    ).status_code == 204
    assert (
        await client.delete(f"/tickets/{tid}/images/{img['id']}")
    ).status_code == 404
    assert list((tmp_path / "uploads").rglob("*.png")) == []
    assert (await client.get(f"/tickets/{tid}")).json()["images"] == []

    task = (
        await client.post(
            f"/tickets/{tid}/tasks", json={"work_date": "2026-08-01", "hours": 1}
        )
    ).json()
    assert (await client.delete(f"/tasks/{task['id']}")).status_code == 204
    assert (await client.get(f"/tickets/{tid}/tasks")).json() == []
    assert (await client.delete("/tasks/12345")).status_code == 404


# ---- login, catalogs ------------------------------------------------------------------------


async def test_everything_but_login_needs_a_valid_token(client):
    anonymous = {"Authorization": ""}
    for path in [
        "/projects",
        "/tickets",
        "/catalogs",
        "/analytics/summary",
        "/users/me",
    ]:
        r = await client.get(path, headers=anonymous)
        assert r.status_code == 401, path
    bad = await client.get("/projects", headers={"Authorization": "Bearer nonsense"})
    assert bad.status_code == 401


async def test_login_rules(client):
    ok = await client.post(
        "/auth/login", data={"username": "ME@example.com", "password": "secret-pass"}
    )
    assert ok.status_code == 200 and ok.json()["token_type"] == "bearer"
    wrong = await client.post(
        "/auth/login", data={"username": "me@example.com", "password": "nope"}
    )
    assert wrong.status_code == 401
    # the first account exists, so registration is closed by default
    closed = await client.post(
        "/auth/register",
        json={"email": "b@example.com", "full_name": "B", "password": "secret-pass"},
    )
    assert closed.status_code == 403


async def test_catalogs_can_be_listed_and_extended(client):
    roots = (await client.get("/catalogs")).json()
    assert [r["code"] for r in roots] == [
        "BILLING_TYPE",
        "PROJECT_STATUS",
        "TICKET_STATUS",
    ]

    created = await client.post(
        "/catalogs/PROJECT_STATUS/items",
        json={"code": "waiting", "name": "Waiting for client", "sort_order": 9},
    )
    assert created.status_code == 201 and created.json()["code"] == "WAITING"
    again = await client.post(
        "/catalogs/PROJECT_STATUS/items", json={"code": "WAITING", "name": "x"}
    )
    assert again.status_code == 409
    assert (await client.get("/catalogs/NOPE/items")).status_code == 404

    # a project can use the new status straight away
    p = await make_project(client, status_id=created.json()["id"])
    assert p["status"]["code"] == "WAITING"

    # deactivated values disappear from the list and can't be picked any more
    off = await client.patch(
        f"/catalogs/PROJECT_STATUS/items/{created.json()['id']}",
        json={"is_active": False},
    )
    assert off.json()["is_active"] is False
    listed = (await client.get("/catalogs/PROJECT_STATUS/items")).json()
    assert "WAITING" not in [i["code"] for i in listed]
    refused = await client.post(
        "/projects",
        json={
            "name": "Y",
            "acronym": "YY",
            "billing_type_id": await item_id(client, "BILLING_TYPE", "HOURLY"),
            "hourly_rate": 5,
            "start_date": "2026-07-01",
            "status_id": created.json()["id"],
        },
    )
    assert refused.status_code == 422
