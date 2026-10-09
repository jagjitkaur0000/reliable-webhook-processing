
import csv
import statistics
import time
import uuid
from pathlib import Path

from sqlalchemy import select

from api.database import SessionLocal
from api.models import WebhookEvent
from api.processor import process_event
from api.processor_no_lock import process_event_no_lock


EVENTS_PER_RUN = 100
REPETITIONS = 5

OUTPUT_FILE = Path("results/processor_comparison.csv")


def create_event(mode, repetition, index):
    event_id = (
        f"benchmark_{mode}_{repetition}_{index}_"
        f"{uuid.uuid4().hex[:12]}"
    )

    with SessionLocal() as db:
        event = WebhookEvent(
            event_id=event_id,
            event_type="research.benchmark",
            payload={"index": index},
            status="received",
        )

        db.add(event)
        db.commit()

    return event_id



def benchmark_one_event(mode, event_id):
    with SessionLocal() as db:

        # Start timing before either implementation
        # performs its first database lookup.
        start = time.perf_counter()

        if mode == "locked":
            event = db.scalar(
                select(WebhookEvent).where(
                    WebhookEvent.event_id == event_id
                )
            )

            success = process_event(db, event)

        elif mode == "no_lock":
            success = process_event_no_lock(
                db,
                event_id
            )

        else:
            raise ValueError(f"Unknown mode: {mode}")

        elapsed_ms = (
            time.perf_counter() - start
        ) * 1000

        if not success:
            raise RuntimeError("Processing failed")

        return elapsed_ms


def main():
    results = []

    for repetition in range(1, REPETITIONS + 1):
        print(f"\nRepetition {repetition}")

        # Alternate the order to reduce order bias.
        modes = (
            ["locked", "no_lock"]
            if repetition % 2 == 1
            else ["no_lock", "locked"]
        )

        for mode in modes:
            latencies = []

            for index in range(EVENTS_PER_RUN):
                event_id = create_event(
                    mode,
                    repetition,
                    index
                )

                latency = benchmark_one_event(
                    mode,
                    event_id
                )

                latencies.append(latency)

                results.append({
                    "repetition": repetition,
                    "mode": mode,
                    "event_id": event_id,
                    "latency_ms": latency,
                })

            print(
                f"{mode}: "
                f"mean={statistics.mean(latencies):.3f} ms, "
                f"median={statistics.median(latencies):.3f} ms"
            )

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
                "event_id",
                "latency_ms",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"\nSaved: {OUTPUT_FILE}")
    print(f"Measurements: {len(results)}")


if __name__ == "__main__":
    main()
