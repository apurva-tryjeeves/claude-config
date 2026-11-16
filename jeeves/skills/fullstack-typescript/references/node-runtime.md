# Node runtime

## Event loop

- Keep each synchronous stretch short; one slow handler delays every request on the process.
- Move CPU-heavy work (large JSON, crypto, image or PDF work, big loops) to a worker thread or a queue consumer.
- Measure event-loop lag (`perf_hooks.monitorEventLoopDelay`) and alert on it.
- Process large arrays in chunks, yielding between them with `setImmediate`.

## Async control

- Await or return every promise; attach handling to each one that runs in the background.
- Bound concurrency: use a pool or limiter for fan-out, sized to the downstream's capacity.
- Pass an `AbortSignal` through every call chain; combine a caller's signal with `AbortSignal.timeout(ms)`.
- Choose the combinator by intent: `Promise.all` (all must succeed), `allSettled` (collect partial failure), `any` or `race` (first wins).
- Run independent awaits together; keep dependent ones sequential.
- Keep request-scoped context (trace id, tenant) in `AsyncLocalStorage`.

## Streams and backpressure

- Stream payloads that can exceed a few megabytes: file transfers, exports, large query results.
- Connect streams with `pipeline` from `node:stream/promises`, which propagates errors and backpressure.
- Page through large tables with a cursor or an async iterator, holding one page in memory.

## Process lifecycle

- On `SIGTERM`: stop accepting work, finish in-flight requests within a deadline, close servers, pools and consumers, then exit.
- Fail fast at startup on invalid configuration.
- Treat `unhandledRejection` and `uncaughtException` as fatal: log, then exit and let the orchestrator restart.
- Size connection pools from the database's limit divided by the instance count.
- Expose liveness and readiness separately.

## Data access

- Select the columns you use; avoid a query inside a loop by batching or joining.
- Keep a transaction short and free of network calls; set a statement timeout.
- Use optimistic locking (a version column) for user-edited rows, and row locks for counters and balances.

## Performance and memory

- Profile before changing code: a CPU profile or flame graph for hot paths, heap snapshots compared over time for leaks.
- Common leak sources: unbounded caches and maps, listeners added per request, timers left running, closures holding large objects.
- Give every cache a size limit and an expiry.

## Testing

- Inject time, randomness and I/O so unit tests are deterministic.
- Test the service layer with real schemas and a fake repository; test repositories against a real database in integration tests.
- Cover each failure path designed in `system-design.md`: timeout, retry, duplicate delivery.
