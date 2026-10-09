
import csv
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sqlalchemy import select

from api.database import SessionLocal
from api.models import WebhookEvent


WORKERS = 5
REPETITIONS = 5
OUTPUT_FILE = Path("results/concurrency_experiment.csv")


def create_event():
    event_id = f"race_{uuid.uuid4().hex}"

    with SessionLocal() as db:
        db.add(
            WebhookEvent(
                event_id=event_id,
                event_type="research.concurrency",
                payload={"test": True},
                status="received",
            )
        )
        db.commit()

    return event_id


def worker(event_id, mode, barrier):
    with SessionLocal() as db:
        query = select(WebhookEvent).where(
            WebhookEvent.event_id == event_id
        )

        if mode == "locked":
            query = query.with_for_update()

        event = db.scalar(query)

        if event.status == "processed":
            db.commit()
            return False

        if mode == "no_lock":
            # Force workers to reach the same point
            # after reading the event.
            barrier.wait(timeout=15)

        event.attempt_count += 1
        event.status = "processed"
        db.commit()

        return True


def run_one(mode, repetition):
    event_id = create_event()

    barrier = threading.Barrier(WORKERS)

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [
            executor.submit(
                worker,
                event_id,
                mode,
                barrier
            )
            for _ in range(WORKERS)
        ]

        outcomes = [future.result() for future in futures]

    with SessionLocal() as db:
        event = db.scalar(
            select(WebhookEvent).where(
                WebhookEvent.event_id == event_id
            )
        )

        return {
            "repetition": repetition,
            "mode": mode,
            "workers": WORKERS,
            "processing_claims": sum(outcomes),
            "final_attempt_count": event.attempt_count,
            "final_status": event.status,
        }


def main():
    results = []

    for repetition in range(1, REPETITIONS + 1):
        for mode in ["no_lock", "locked"]:
            result = run_one(mode, repetition)
            results.append(result)
            print(result)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "repetition",
                "mode",
                "workers",
                "processing_claims",
                "final_attempt_count",
                "final_status",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"\nSaved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
