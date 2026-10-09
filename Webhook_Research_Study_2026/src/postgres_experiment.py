
import csv
import statistics
import time
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app


UNIQUE_EVENTS = 100
DUPLICATE_EVENTS = 20

OUTPUT_FILE = Path("results/postgres_pilot.csv")


def measure_request(client, method, url, **kwargs):
    start = time.perf_counter()

    response = client.request(
        method,
        url,
        **kwargs
    )

    latency_ms = (
        time.perf_counter() - start
    ) * 1000

    return response, latency_ms


def run_experiment():
    rows = []
    event_ids = []
    run_id = uuid.uuid4().hex[:12]

    with TestClient(app) as client:

        # Create unique webhook events
        for i in range(UNIQUE_EVENTS):
            event_id = f"benchmark_{run_id}_{i}"
            event_ids.append(event_id)

            response, latency = measure_request(
                client,
                "POST",
                "/webhooks",
                json={
                    "event_id": event_id,
                    "event_type": "order.created",
                    "payload": {"order_id": i}
                }
            )

            assert response.status_code == 200
            assert response.json()["status"] == "received"

            rows.append({
                "operation": "receive_unique",
                "event_id": event_id,
                "status": response.json()["status"],
                "latency_ms": latency
            })

        # Send duplicate webhook deliveries
        for event_id in event_ids[:DUPLICATE_EVENTS]:
            response, latency = measure_request(
                client,
                "POST",
                "/webhooks",
                json={
                    "event_id": event_id,
                    "event_type": "order.created",
                    "payload": {"order_id": 999}
                }
            )

            assert response.status_code == 200
            assert response.json()["status"] == "duplicate"

            rows.append({
                "operation": "receive_duplicate",
                "event_id": event_id,
                "status": response.json()["status"],
                "latency_ms": latency
            })

        # Process each unique event
        for event_id in event_ids:
            response, latency = measure_request(
                client,
                "POST",
                f"/events/{event_id}/process"
            )

            assert response.status_code == 200
            assert response.json()["status"] == "processed"

            rows.append({
                "operation": "process",
                "event_id": event_id,
                "status": response.json()["status"],
                "latency_ms": latency
            })

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
                "operation",
                "event_id",
                "status",
                "latency_ms"
            ]
        )
        writer.writeheader()
        writer.writerows(rows)

    print("\nPOSTGRESQL EXPERIMENT RESULTS")
    print("-----------------------------")

    for operation in [
        "receive_unique",
        "receive_duplicate",
        "process"
    ]:
        latencies = [
            row["latency_ms"]
            for row in rows
            if row["operation"] == operation
        ]

        print(f"\nOperation: {operation}")
        print(f"Requests: {len(latencies)}")
        print(
            "Mean latency: "
            f"{statistics.mean(latencies):.3f} ms"
        )
        print(
            "Median latency: "
            f"{statistics.median(latencies):.3f} ms"
        )

    print(f"\nResults saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    run_experiment()
