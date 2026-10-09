
import uuid

import pytest
from fastapi.testclient import TestClient

from api.main import app
from concurrent.futures import ThreadPoolExecutor


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def create_event(client, event_id):
    response = client.post(
        "/webhooks",
        json={
            "event_id": event_id,
            "event_type": "order.created",
            "payload": {
                "order_id": 101,
                "amount": 500,
            },
        },
    )
    return response


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_webhook_creation(client):
    event_id = f"test_{uuid.uuid4().hex}"

    response = create_event(client, event_id)

    assert response.status_code == 200
    assert response.json()["status"] == "received"


def test_duplicate_webhook(client):
    event_id = f"test_{uuid.uuid4().hex}"

    first = create_event(client, event_id)
    second = create_event(client, event_id)

    assert first.status_code == 200
    assert first.json()["status"] == "received"

    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"


def test_simulated_failure_and_retry(client):
    event_id = f"test_{uuid.uuid4().hex}"

    create_event(client, event_id)

    failed = client.post(
        f"/events/{event_id}/process",
        params={"simulate_failure": True},
    )

    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"
    assert failed.json()["attempt_count"] == 1

    retried = client.post(
        f"/events/{event_id}/retry"
    )

    assert retried.status_code == 200
    assert retried.json()["status"] == "processed"
    assert retried.json()["attempt_count"] == 2


def test_retry_rejected_for_unfailed_event(client):
    event_id = f"test_{uuid.uuid4().hex}"

    create_event(client, event_id)

    response = client.post(
        f"/events/{event_id}/retry"
    )

    assert response.status_code == 409


def test_concurrent_duplicate_webhooks():
    event_id = f"concurrent_{uuid.uuid4().hex}"

    payload = {
        "event_id": event_id,
        "event_type": "payment.completed",
        "payload": {
            "order_id": 500,
            "amount": 1000
        }
    }

    def send_request(_):
        with TestClient(app) as client:
            response = client.post(
                "/webhooks",
                json=payload
            )
            return response

    with ThreadPoolExecutor(max_workers=10) as executor:
        responses = list(
            executor.map(send_request, range(10))
        )

    assert all(
        response.status_code == 200
        for response in responses
    )

    statuses = [
        response.json()["status"]
        for response in responses
    ]

    assert statuses.count("received") == 1
    assert statuses.count("duplicate") == 9


def test_concurrent_processing():
    event_id = f"processing_{uuid.uuid4().hex}"

    with TestClient(app) as client:
        created = create_event(client, event_id)
        assert created.status_code == 200

    def process_request(_):
        with TestClient(app) as client:
            return client.post(
                f"/events/{event_id}/process"
            )

    with ThreadPoolExecutor(max_workers=10) as executor:
        responses = list(
            executor.map(process_request, range(10))
        )

    assert all(
        response.status_code == 200
        for response in responses
    )

    with TestClient(app) as client:
        result = client.post(
            f"/events/{event_id}/process"
        )

    assert result.json()["status"] == "processed"
    assert result.json()["attempt_count"] == 1

