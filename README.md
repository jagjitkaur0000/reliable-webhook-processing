# Reliable Event / Webhook Processing System

**Status: Work in progress**

A backend engineering project exploring how to ingest, persist, and process webhook events reliably, including duplicate delivery, transient failures, and asynchronous processing.

## Technology
- Python, FastAPI
- PostgreSQL, SQLAlchemy
- Docker

## Scope and progress
- **In progress:** HTTP endpoint for receiving webhook events and storing incoming events durably.
- **In progress:** Database-level idempotency to prevent processing the same event more than once.
- **In progress:** Event persistence models using PostgreSQL and SQLAlchemy.
- **Development environment:** Docker-based local development.
- **Planned / being implemented:** Asynchronous workers, retry scheduling, failure handling, and dead-letter processing.

> This repository documents work in progress. A feature listed here should not be assumed complete until its implementation and tests are committed.

## Proposed processing flow
```text
Webhook sender -> FastAPI ingestion endpoint -> PostgreSQL event store
                                              |
                                              v
                                       Background worker
                                              |
                                      success / retry
                                              |
                                       dead-letter state
```

## Reliability goals
1. **Durable receipt:** persist an event before acknowledging it, subject to the endpoint's final design.
2. **Idempotency:** use a stable event identifier and a database uniqueness constraint to reject or safely handle duplicate deliveries.
3. **Recoverability:** retain processing state to resume after a worker crash.
4. **Retry safety:** distinguish retryable errors from permanent failures.
5. **Observability:** expose event status and failure details without logging secrets.

## Proposed data model
| Field | Purpose |
| --- | --- |
| `event_id` | Sender's unique event identifier (idempotency key) |
| `event_type` | Type of webhook event |
| `payload` | JSON payload |
| `status` | received / processing / processed / failed |
| `attempt_count` | Number of processing attempts |
| `next_retry_at` | Scheduled retry time |
| `received_at` | Receipt timestamp |
| `processed_at` | Successful completion timestamp |

*Schema is a design proposal and may change as implementation progresses.*

## Planned validation and experiments
The following are **planned experiments, not completed results**:
- Send the same `event_id` repeatedly and verify that it produces one logical event record.
- Interrupt a worker during processing and verify that the event can be recovered.
- Inject temporary handler failures and verify bounded retries and eventual success or failure state.
- Measure processing latency and throughput under increasing event volume.

Once implemented, record setup, test commands, dataset sizes, results, and limitations in `docs/experiments.md`.

## Running locally
Setup instructions and verified commands will be added when the initial application and Docker configuration are committed. **This README does not claim the service is runnable yet.**

## Roadmap
- [ ] Commit initial FastAPI application and PostgreSQL models
- [ ] Implement and test ingestion endpoint
- [ ] Enforce database uniqueness for idempotency
- [ ] Add event status transitions
- [ ] Implement worker and retry mechanism
- [ ] Add automated reliability tests
- [ ] Document experiment results and limitations

## Motivation
Webhook providers commonly deliver events more than once, while processing workers can fail after receipt. This project studies practical backend design techniques for managing duplicate deliveries and transient failures with persistent state and repeatable tests.

## Author
Jagjit Kaur — [GitHub profile](https://github.com/jagjitkaur0000)
