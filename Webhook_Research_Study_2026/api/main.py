
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from api.processor import process_event
from fastapi import HTTPException

from api.database import Base, engine, get_db
from api.models import WebhookEvent
from api.schemas import WebhookRequest, WebhookResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Webhook Reliability Research API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhooks", response_model=WebhookResponse)
def receive_webhook(
    event: WebhookRequest,
    db: Session = Depends(get_db),
):
    existing = db.scalar(
        select(WebhookEvent).where(
            WebhookEvent.event_id == event.event_id
        )
    )

    if existing:
        return WebhookResponse(
            event_id=event.event_id,
            status="duplicate",
            message="Event already received",
        )

    record = WebhookEvent(
        event_id=event.event_id,
        event_type=event.event_type,
        payload=event.payload,
        status="received",
    )

    db.add(record)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        # The unique constraint prevents competing inserts.
        return WebhookResponse(
            event_id=event.event_id,
            status="duplicate",
            message="Event already received",
        )

    return WebhookResponse(
        event_id=event.event_id,
        status="received",
        message="Webhook stored successfully",
    )
    
@app.post("/events/{event_id}/process")
def process_webhook_event(
    event_id: str,
    simulate_failure: bool = False,
    db: Session = Depends(get_db),
):
    event = db.scalar(
        select(WebhookEvent).where(
            WebhookEvent.event_id == event_id
        )
    )

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="Event not found",
        )

    success = process_event(
        db,
        event,
        simulate_failure=simulate_failure,
    )

    return {
        "event_id": event.event_id,
        "status": event.status,
        "attempt_count": event.attempt_count,
        "success": success,
        "last_error": event.last_error,
    }


@app.post("/events/{event_id}/retry")
def retry_webhook_event(
    event_id: str,
    db: Session = Depends(get_db),
):
    event = db.scalar(
        select(WebhookEvent).where(
            WebhookEvent.event_id == event_id
        )
    )

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="Event not found",
        )

    if event.status != "failed":
        raise HTTPException(
            status_code=409,
            detail="Only failed events can be retried",
        )

    success = process_event(
        db,
        event,
        simulate_failure=False,
    )

    return {
        "event_id": event.event_id,
        "status": event.status,
        "attempt_count": event.attempt_count,
        "success": success,
        "last_error": event.last_error,
    }


