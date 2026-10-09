# Experimental Results and Analysis

**Research topic:** Experimental Evaluation of Idempotency, Retry Mechanisms, and Concurrency Control in Webhook Processing

**Study period:** September–October 2026

## 1. Research Objective

The objective of this study was to evaluate how idempotency, retry mechanisms, and database concurrency control affect the reliability of webhook processing.

The experiments focused on three questions:

1. How does event-ID deduplication affect duplicate processing?
2. How do immediate retries affect recovery from simulated transient failures?
3. How does PostgreSQL row-level locking affect concurrent attempts to process the same event?

The study combined a controlled SQLite simulation with a local FastAPI and PostgreSQL implementation.

## 2. SQLite Simulation

### Experimental Setup

Three processing strategies were compared:

- **Baseline:** Successful webhook deliveries produce recorded effects without duplicate protection.
- **Idempotent:** Event-ID deduplication prevents repeated deliveries from producing additional effects.
- **Idempotent with retries:** Deduplication is combined with up to three immediate processing attempts.

Each repetition used 200 unique event identifiers and 50 additional duplicate deliveries. Transient failures were simulated for 10% of unique event identifiers before processing effects occurred.

Five repetitions were conducted using deterministic random seeds.

### Experimental Results

| Strategy | Successful requests | Failed requests | Unique effects | Duplicate effects |
|---|---:|---:|---:|---:|
| Baseline | 230 | 20 | 185.8 | 44.2 |
| Idempotent | 230 | 20 | 185.8 | 0 |
| Idempotent with retries | 250 | 0 | 200 | 0 |

Values represent averages across five repetitions.

### Analysis

The baseline configuration produced an average of 44.2 duplicate effects because repeated successful deliveries could generate additional effects.

The idempotent configuration eliminated duplicate effects in the simulated workload. However, events affected by transient failures were not automatically recovered.

Combining idempotency with immediate retries recovered the simulated failures and produced 200 unique effects without duplicate effects.

These findings apply to the defined failure model. They do not establish exactly-once processing in a distributed production system.

## 3. FastAPI and PostgreSQL Implementation

A webhook processing API was implemented using FastAPI, SQLAlchemy, and PostgreSQL.

The implementation includes:

- Webhook reception and JSON payload validation
- Unique event-ID enforcement
- Duplicate request detection
- Persistent event status tracking
- Simulated transient processing failures
- Manual retry endpoints
- PostgreSQL row-level locking using `SELECT FOR UPDATE`

Automated tests were used to evaluate API functionality and concurrent processing behavior.

Seven API integration tests and two processor comparison tests passed during the recorded testing stage.

The PostgreSQL uniqueness constraint prevented duplicate event records in the tested scenarios. However, database record uniqueness alone does not guarantee exactly-once execution of external business operations.

## 4. PostgreSQL Request Latency Evaluation

### Experimental Setup

Six measurement runs were conducted using FastAPI's in-process TestClient and a local PostgreSQL database.

Each run included:

- 100 unique webhook deliveries
- 20 duplicate webhook deliveries
- 100 event-processing requests

A total of 1,320 requests were measured across the six runs.

### Results

| Operation | Mean latency |
|---|---:|
| Receive unique webhook | 5.744 ms |
| Receive duplicate webhook | 4.796 ms |
| Process webhook | 8.677 ms |

### Analysis

Event-processing requests had a higher observed average latency than webhook reception and duplicate detection.

These measurements include application processing and local database operations. They do not include external network transmission or deployment-related overhead.

The results describe the local experimental environment and should not be interpreted as production throughput measurements.

## 5. Sequential Processing Comparison

### Experimental Setup

Two event-processing implementations were evaluated:

- Processing with explicit PostgreSQL row-level locking
- Processing without explicit row-level locking

Each implementation processed 100 events per repetition across five repetitions, resulting in 500 measurements per configuration.

The corrected benchmark measured the complete processing path, beginning before the initial database lookup.

### Results

| Implementation | Mean latency |
|---|---:|
| With row-level locking | 4.876 ms |
| Without explicit row-level locking | 3.816 ms |

### Analysis

The implementation using explicit locking showed a higher observed mean latency in the sequential benchmark.

However, the two implementations have different internal query patterns. The locking implementation performs an additional database lookup.

Therefore, the measured difference represents the performance of the complete implementations rather than the isolated overhead of PostgreSQL row-level locking.

The initial exploratory benchmark is preserved separately, while the corrected benchmark is used for the main comparison.

## 6. Controlled Concurrency Experiment

### Experimental Setup

The concurrency experiment evaluated five workers attempting to process the same webhook event.

Two configurations were compared:

- Processing without explicit row-level locking
- Processing using PostgreSQL `SELECT FOR UPDATE`

Each configuration was tested across five repetitions.

The non-locking implementation used a synchronization barrier to deliberately expose a race condition. The locking implementation serialized access through PostgreSQL.

### Results

| Metric | Without locking | With locking |
|---|---:|---:|
| Concurrent workers | 5 | 5 |
| Repetitions | 5 | 5 |
| Workers claiming processing per repetition | 5 | 1 |
| Final stored attempt count | 1 | 1 |

### Analysis

Without explicit locking, all five workers read the initial unprocessed state and entered the processing branch.

The final attempt count remained one, demonstrating a lost-update pattern under the controlled synchronization conditions.

With PostgreSQL row-level locking, only one worker entered the processing branch. The remaining workers observed the updated event state.

This experiment demonstrates how row-level locking can prevent competing workers from independently claiming the same database event in the tested scenario.

It does not demonstrate exactly-once execution of external operations such as payments, emails, or third-party API requests.

## 7. Reproducibility

The project contains source code, automated tests, raw experimental measurements, and summary data.

The SQLite simulation was reproduced using the same workload configuration and random seeds. Functional results matched between the original and repeated runs, while timing measurements varied.

The PostgreSQL experiments were conducted using a local database environment.

The experimental scripts and corresponding CSV files are included in the repository.

## 8. Limitations

The study has several limitations:

- SQLite failures were simulated and occurred before recorded effects.
- Retry attempts were immediate and did not use exponential backoff.
- PostgreSQL retry handling was manually triggered rather than automatically scheduled.
- Request latency measurements used an in-process TestClient.
- The sequential comparison did not isolate locking overhead.
- The concurrency experiment used deliberately synchronized workers.
- External business effects, distributed processing, crash recovery, and production load testing were not evaluated.

These limitations restrict the generalizability of the findings.

## 9. Conclusion

The experiments demonstrated that event-ID deduplication eliminated duplicate recorded effects in the controlled SQLite simulation, while immediate retries recovered the simulated transient failures.

The PostgreSQL implementation demonstrated duplicate event-record prevention and supported testing of concurrent processing behavior.

In the controlled concurrency experiment, explicit row-level locking restricted processing claims to one worker, whereas the non-locking implementation allowed multiple workers to enter the processing branch.

Overall, the study provides experimental evidence of the behavior of selected webhook reliability mechanisms under defined local workloads. Further evaluation would be required to establish reliability guarantees in distributed production systems.

## 10. Supporting Files

- `src/experiment.py`
- `src/postgres_experiment.py`
- `src/processor_benchmark.py`
- `src/concurrency_experiment.py`
- `tests/`
- `results/`
- `Jagjit_Kaur_Webhook_Research_Final_Report.pdf`

## Author

**Jagjit Kaur**  
Independent Experimental Study  
October 2026