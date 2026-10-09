
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models import WebhookEvent


def process_event_no_lock(
    db: Session,
    event_id: str,
    simulate_failure: bool = False
) -> bool:
    """Process an event without explicit row-level locking."""

    try:
        event = db.scalar(
            select(WebhookEvent).where(
                WebhookEvent.event_id == event_id
            )
        )

        if event is None:
            raise ValueError("Event not found")

        if event.status == "processed":
            db.commit()
            return True

        event.attempt_count += 1

        if simulate_failure and event.attempt_count == 1:
            event.status = "failed"
            event.last_error = "Simulated transient failure"
            db.commit()
            return False

        event.status = "processed"
        event.last_error = None

        db.commit()
        return True

    except Exception:
        db.rollback()
        raise
