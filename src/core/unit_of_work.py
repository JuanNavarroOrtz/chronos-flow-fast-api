from typing import Protocol


class UnitOfWork(Protocol):
    """Owns the transaction. Repositories stage changes; the use case decides when to commit."""

    async def commit(self) -> None: ...
