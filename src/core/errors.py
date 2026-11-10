class DomainError(Exception):
    """Base class for business-rule errors (mapped to HTTP codes at the edge)."""


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    """The request is valid but clashes with the current state (e.g. deleting a used project)."""


class DuplicateError(ConflictError):
    pass


class InvalidDataError(DomainError):
    pass


class UnauthorizedError(DomainError):
    """Missing or wrong credentials / token."""


class ForbiddenError(DomainError):
    """Authenticated (or not needed) but not allowed to do this."""
