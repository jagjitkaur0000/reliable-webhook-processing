# Reliable Webhook Processing — Independent Experimental Study

An independent experimental study of idempotency, retry mechanisms, and concurrency control in webhook processing. The project combines an in-memory SQLite simulation with a FastAPI, SQLAlchemy, and PostgreSQL prototype and records results from repeatable local experiments.

## Research question

How do event-ID deduplication, bounded retries, and PostgreSQL row-level locking affect duplicate processing, recovery from simulated transient failures, and concurrent event processing?

## Technology

- Python 3.13
- SQLite
- FastAPI and SQLAlchemy
- PostgreSQL 16
- pytest and HTTPX

## Experimental design

### 1. SQLite simulation

Three conditions were compared:

- **Baseline:** Each successful delivery records an effect.
- **Idempotent:** Repeated deliveries with the same event ID do not record another effect.
- **Idempotent + retry:** Event-ID deduplication with up to three immediate attempts for simulated transient failures.

Each repetition used 200 unique events, 50 duplicate deliveries, and simulated first-attempt failures for 10% of unique event IDs. Five repetitions were conducted. This is an in-memory simulation, not a network or PostgreSQL performance benchmark.

### 2. FastAPI and PostgreSQL prototype

The prototype provides webhook ingestion, event-ID uniqueness enforcement, persisted event status, deterministic failure simulation, manual retry endpoints, and alternative processing implementations with and without explicit `SELECT ... FOR UPDATE` locking.

### 3. Local benchmarks and concurrency tests

- Six in-process FastAPI TestClient measurement runs, each covering 100 unique deliveries, 20 duplicate deliveries, and 100 processing requests.
- Five repetitions of a sequential processor comparison with 100 events per implementation per repetition.
- Five repetitions of a controlled concurrency test with five workers competing to process the same event.

The no-lock concurrency test uses a synchronization barrier to reproduce a race condition deliberately. The two processor implementations have different query paths, so their sequential timing difference cannot be attributed solely to lock acquisition.

## Results

### SQLite simulation

| Configuration | Mean unique effects | Mean duplicate effects | Mean failed requests |
| --- | ---: | ---: | ---: |
| Baseline | 185.8 | 44.2 | 20 |
| Idempotent | 185.8 | 0 | 20 |
| Idempotent + retry | 200 | 0 | 0 |

### PostgreSQL prototype: in-process request latency

| Operation | Mean latency across six runs |
| --- | ---: |
| Unique webhook delivery | 5.744 ms |
| Duplicate webhook delivery | 4.796 ms |
| Process event | 8.677 ms |

These are local TestClient measurements, not deployed HTTP server or network benchmarks.

### Sequential processor comparison

| Implementation | Mean complete-path latency |
| --- | ---: |
| With explicit row-level locking | 4.876 ms |
| Without explicit row-level locking | 3.816 ms |

### Controlled concurrency experiment

Across five repetitions with five workers per repetition, the no-lock implementation recorded five processing claims per repetition, while the locked implementation recorded one. Both finished with a stored attempt count of one. These processing claims are decisions inside the test code, not confirmed external side effects.

## Setup

Run the following commands from the project root.

Create and activate a virtual environment on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install pytest fastapi "uvicorn[standard]" sqlalchemy "psycopg[binary]" python-dotenv httpx
```

Create a **disposable local PostgreSQL database** and set its connection URL in a private `.env` file:

```env
DATABASE_URL=postgresql+psycopg://YOUR_USER:YOUR_PASSWORD@localhost:5432/webhook_research
```

Do not commit `.env` or database credentials. The prototype creates tables through SQLAlchemy but does not include a complete migration system. If reusing an older database, verify that its schema matches `api/models.py`, including `attempt_count` and `last_error`.

Start the API:

```powershell
python -m uvicorn api.main:app --reload
```

API documentation is available locally at `http://127.0.0.1:8000/docs`.

## Tests and reproduction

Run the automated tests:

```powershell
python -m pytest tests -v
```

Run the SQLite simulation into a new output folder:

```powershell
python src/experiment.py --unique 200 --repeats 5 --seed 42 --out results/reproduction_new
```

Run the PostgreSQL experiments:

```powershell
python -m src.postgres_experiment
python -m src.processor_benchmark
python -m src.concurrency_experiment
```

**Note:** The PostgreSQL tests and scripts insert database records. Some benchmark scripts overwrite their output CSV files. Use a disposable research database and back up existing results before rerunning experiments.

## Repository structure

```text
api/       FastAPI application, database models, and processor implementations
src/       SQLite simulation and PostgreSQL experiment scripts
tests/     Unit and integration tests
results/   Raw experiment data, summaries, and environment information
docs/      Analysis and submission notes
README.md  Project overview and reproduction instructions
```

## Evidence files

- `results/pilot_run_01/` — initial SQLite experiment
- `results/reproduction_01/` — SQLite reproduction
- `results/postgres_pilot_run_01.csv` through `postgres_pilot_run_06.csv` — six local integration measurement runs
- `results/processor_comparison.csv` — corrected sequential benchmark
- `results/processor_comparison_initial.csv` — earlier benchmark with unequal timing boundaries, retained for transparency
- `results/concurrency_experiment.csv` — controlled concurrency observations

## Limitations

The experiments use simulated pre-effect failures and local database operations. The prototype does not implement durable automatic retry scheduling, distributed worker recovery, production message queues, real external side effects, or crash-restart testing. The concurrency test deliberately creates contention, and the results do not establish exactly-once execution of external operations. Timing values are specific to the local environment.

## Conclusion

Within the SQLite simulation, event-ID deduplication prevented duplicate recorded effects, and immediate retries recovered the selected transient failures. In the controlled PostgreSQL concurrency experiment, row-level locking prevented multiple workers from claiming the same event in the tested scenario. The project documents these results and their limitations for further study.

## References

- [PostgreSQL: Explicit Locking](https://www.postgresql.org/docs/16/explicit-locking.html)
- [PostgreSQL: INSERT and ON CONFLICT](https://www.postgresql.org/docs/16/sql-insert.html)
- [FastAPI: Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/en/20/orm/)
- [pytest Documentation](https://docs.pytest.org/)

## Author

Jagjit Kaur  
Independent experimental study, October 2026
