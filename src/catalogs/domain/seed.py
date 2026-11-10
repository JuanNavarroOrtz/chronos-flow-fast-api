"""Default catalogs, inserted on startup if missing (there are no migrations to do it)."""

from src.catalogs.domain.entities import (
    BILLING_TYPE,
    FIXED,
    HOURLY,
    PROJECT_STATUS,
    TICKET_STATUS,
)

# catalog code -> (catalog name, [(value code, value name), ...] in display order)
SEED: dict[str, tuple[str, list[tuple[str, str]]]] = {
    BILLING_TYPE: (
        "Billing type",
        [(HOURLY, "Per hour"), (FIXED, "Fixed price")],
    ),
    PROJECT_STATUS: (
        "Project status",
        [
            ("ACTIVE", "Active"),
            ("ON_HOLD", "On hold"),
            ("COMPLETED", "Completed"),
            ("CANCELLED", "Cancelled"),
        ],
    ),
    TICKET_STATUS: (
        "Ticket status",
        [("OPEN", "Open"), ("IN_PROGRESS", "In progress"), ("CLOSED", "Closed")],
    ),
}
