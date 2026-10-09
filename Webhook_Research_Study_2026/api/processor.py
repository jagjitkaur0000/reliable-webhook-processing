
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models import WebhookEvent


def process_event(
    db: Session,
    event: WebhookEvent,
    simulate_failure: bool = False
) -> bool:
    """Process an event while holding a PostgreSQL row lock."""

    try:
        # Lock the row until the transaction commits.
        locked_event = db.scalar(
            select(WebhookEvent)
            .where(WebhookEvent.id == event.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        if locked_event is None:
            raise ValueError("Event not found")

        # Already processed: do not process again.
        if locked_event.status == "processed":
            db.commit()
            return True

        locked_event.attempt_count += 1

        if simulate_failure and locked_event.attempt_count == 1:
            locked_event.status = "failed"
            locked_event.last_error = "Simulated transient failure"
            db.commit()
            return False

        locked_event.status = "processed"
        locked_event.last_error = None

        db.commit()
        return True

    except Exception:
        db.rollback()
        raise
