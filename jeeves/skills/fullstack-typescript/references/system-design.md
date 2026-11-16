# System design

Design from requirements to components; each choice names the requirement it serves.

## Requirements

- Write the numbers first: requests per second, payload size, p99 latency, data growth per month, availability target.
- Name the consistency each operation needs: strict (money, inventory), read-your-writes (user edits), eventual (feeds, analytics).
- Name the callers and their trust level.

## Data

- Give every table or collection one owning service; other services go through its API or events.
- Design from access patterns: list the queries, then the indexes that serve them.
- Store money as integer minor units with a currency; store time in UTC.
- Migrate in three deploys: add (backward compatible), backfill and switch reads, remove. Each deploy stays reversible.
- Paginate every list endpoint with a cursor and a maximum page size.

## Correctness under retries

- Treat every network call as "may run twice". Give each write an idempotency key, stored with a unique constraint.
- Publish events through a transactional outbox: the state change and the event row commit together, and a relay delivers.
- Make consumers idempotent: record the handled message id in the same transaction as the effect.
- Order only where the domain needs it, by a partition key such as the account id.

## Consistency across services

| Need | Use |
|---|---|
| One service, one database | A database transaction |
| Several services, steps can be undone | A saga with compensating steps |
| Derived or reporting data | Events plus a periodic reconciliation job |

Hold a lock or transaction for the shortest span, and keep network calls outside it.

## Scaling

- Keep services stateless; put session and job state in a store.
- Cache with a stated owner, time-to-live and invalidation trigger. Protect against stampedes with a single-flight or a jittered expiry.
- Move slow or bursty work to a queue; size consumers by the queue's age, and give each queue a dead-letter queue and an alert.
- Bound everything: request size, page size, concurrency, queue depth, retry count.
- Rate-limit per caller at the edge.

## Failure

- Set a timeout on every outbound call, shorter than the caller's own.
- Retry only idempotent calls, with exponential backoff, jitter and a cap.
- Add a circuit breaker to a dependency that can stall, and define the degraded behaviour.
- Limit blast radius: per-tenant limits, bulkheads between workloads, feature flags per tenant.
- Define health (process alive) and readiness (dependencies reachable) separately.

## Evolution

- Version public contracts; add fields as optional and keep old readers working for one release.
- Ship behind a flag, ramp by percentage or tenant, and write the rollback step in the design.
- Record each significant decision in a short note: context, decision, trade-off, rejected option.

## Design section template

1. Requirements and numbers
2. Components and data flow
3. Data model and migrations
4. Contracts (API, events)
5. Failure modes and their handling
6. Security notes
7. Rollout and rollback
8. Open questions
