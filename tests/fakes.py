"""In-memory stand-ins for the ports. They let use cases run with no database and no disk."""

from datetime import date
from decimal import Decimal

from src.catalogs.domain.entities import FIXED, HOURLY, CatalogItem
from src.catalogs.use_cases.catalog_use_cases import CatalogUseCases
from src.projects.domain.entities import ProjectEntity

# Catalog values for tests that build entities directly (no repository involved).
HOURLY_ITEM = CatalogItem(1, HOURLY, "Per hour")
FIXED_ITEM = CatalogItem(2, FIXED, "Fixed price")
ACTIVE_ITEM = CatalogItem(3, "ACTIVE", "Active")


def make_project(acronym: str = "IC", **overrides) -> ProjectEntity:
    fields = {
        "name": "iCargo",
        "acronym": acronym,
        "billing_type": HOURLY_ITEM,
        "status": ACTIVE_ITEM,
        "hourly_rate": Decimal("7.00"),
        "start_date": date(2026, 7, 1),
    } | overrides
    return ProjectEntity(**fields)


class FakeProjectRepo:
    def __init__(self):
        self.projects, self.ticket_counts = {}, {}

    async def add(self, project):
        project.id = len(self.projects) + 1
        self.projects[project.id] = project
        return project

    async def get(self, project_id):
        return self.projects.get(project_id)

    async def get_by_acronym(self, acronym):
        return next((p for p in self.projects.values() if p.acronym == acronym), None)

    async def list(self):
        return list(self.projects.values())

    async def update(self, project):
        return project

    async def delete(self, project_id):
        self.projects.pop(project_id, None)

    async def ticket_count(self, project_id):
        return self.ticket_counts.get(project_id, 0)


class FakeTicketRepo:
    def __init__(self):
        self.tickets, self.images, self.fail_add_image = {}, {}, False

    async def add(self, ticket):
        ticket.id = len(self.tickets) + 1
        self.tickets[ticket.id] = ticket
        return ticket

    async def get(self, ticket_id):
        return self.tickets.get(ticket_id)

    async def get_by_code(self, code):
        return next((t for t in self.tickets.values() if t.code == code), None)

    async def list(self, project_id=None):
        return [t for t in self.tickets.values() if project_id in (None, t.project_id)]

    async def update(self, ticket):
        return ticket

    async def delete(self, ticket_id):
        self.tickets.pop(ticket_id, None)

    async def add_image(self, image):
        if self.fail_add_image:
            raise RuntimeError("db down")
        image.id = len(self.images) + 1
        self.images[image.id] = image
        self.tickets[image.ticket_id].images.append(image)
        return image

    async def remove_image(self, ticket_id, image_id):
        image = self.images.get(image_id)
        if image is None or image.ticket_id != ticket_id:
            return None
        del self.images[image_id]
        self.tickets[ticket_id].images.remove(image)
        return image


class FakeUow:
    def __init__(self):
        self.commits, self.fail = 0, False

    async def commit(self):
        if self.fail:
            raise RuntimeError("commit failed")
        self.commits += 1


class FakeStorage:
    def __init__(self):
        self.files, self._n = set(), 0

    async def save(self, ticket_id, extension, data):
        self._n += 1
        path = f"{ticket_id}/{self._n}{extension}"
        self.files.add(path)
        return path

    async def delete(self, paths):
        self.files.difference_update(paths)


class FakeCatalogRepo:
    def __init__(self):
        self.rows = {}

    async def get(self, catalog_id):
        return self.rows.get(catalog_id)

    async def get_by_code(self, code, parent_id):
        return next(
            (
                r
                for r in self.rows.values()
                if r.code == code and r.parent_id == parent_id
            ),
            None,
        )

    async def list_roots(self):
        return [r for r in self.rows.values() if r.parent_id is None]

    async def list_children(self, parent_id, only_active=True):
        rows = [
            r
            for r in self.rows.values()
            if r.parent_id == parent_id and (r.is_active or not only_active)
        ]
        return sorted(rows, key=lambda r: (r.sort_order, r.id))

    async def add(self, entry):
        entry.id = len(self.rows) + 1
        self.rows[entry.id] = entry
        return entry

    async def update(self, entry):
        return entry


async def seeded_catalogs() -> CatalogUseCases:
    """Catalog use cases over an in-memory repo that already holds the default catalogs."""
    uc = CatalogUseCases(FakeCatalogRepo(), FakeUow())
    await uc.seed_defaults()
    return uc


class FakeUserRepo:
    def __init__(self):
        self.users = {}

    async def add(self, user):
        user.id = len(self.users) + 1
        self.users[user.id] = user
        return user

    async def get(self, user_id):
        return self.users.get(user_id)

    async def get_by_email(self, email):
        return next((u for u in self.users.values() if u.email == email), None)

    async def count(self):
        return len(self.users)


class FakeHasher:
    def hash(self, password):
        return f"hashed:{password}"

    def verify(self, password, password_hash):
        return password_hash == f"hashed:{password}"


class FakeTokens:
    def issue(self, user_id):
        return f"token-{user_id}"

    def subject_of(self, token):
        return int(token.removeprefix("token-")) if token.startswith("token-") else None
