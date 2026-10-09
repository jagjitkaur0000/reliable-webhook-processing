
import uuid

from sqlalchemy import select

from api.database import SessionLocal
from api.models import WebhookEvent
from api.processor import process_event
from api.processor_no_lock import process_event_no_lock


def create_test_event():
    event_id = f"comparison_{uuid.uuid4().hex}"

    with SessionLocal() as db:
        event = WebhookEvent(
            event_id=event_id,
            event_type="research.test",
            payload={"source": "comparison"},
            status="received",
        )
        db.add(event)
        db.commit()

    return event_id


def test_processor_without_lock():
    event_id = create_test_event()

    with SessionLocal() as db:
        success = process_event_no_lock(db, event_id)

        event = db.scalar(
            select(WebhookEvent).where(
                WebhookEvent.event_id == event_id
            )
        )

        assert success is True
        assert event.status == "processed"
        assert event.attempt_count == 1


def test_processor_with_lock():
    event_id = create_test_event()

    with SessionLocal() as db:
        event = db.scalar(
            select(WebhookEvent).where(
                WebhookEvent.event_id == event_id
            )
        )

        success = process_event(db, event)

        db.refresh(event)

        assert success is True
        assert event.status == "processed"
        assert event.attempt_count == 1
