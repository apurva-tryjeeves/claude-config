---
name: structured-logging
description: Structured logging conventions for Jeeves microservices — logger naming, levels, fields, timing and redaction. Trigger when adding or reviewing `logger.*` calls, naming a logger or log prefix, replacing `console.*`, timing an external call or query, or reviewing how a service logs.
---

# Structured Logging — Jeeves Microservices

Structured-logging conventions for services on `@jeevesinc/jeeves-telemetry`
(pino + OTel under the hood). Write new code with its `getLogger`.

| Logger in the repo | Call order | Repos |
|---|---|---|
| `@jeevesinc/jeeves-telemetry` `getLogger` (pino) | fields object first, message last — rule 4 below | most services |
| winston `createLogger` (`src/config/winston.js`) | message first, metadata object second | authentication-service, open-banking-service |

In a winston repo, keep winston's order on existing loggers and use
`getLogger` for new modules.

## 1. One logger per module, created once

```typescript
import { getLogger } from '@jeevesinc/jeeves-telemetry';

const logger = getLogger('moduleResponsibility'); // e.g. 'paymentReconciliation'
```

Create the logger once per module/file, store it in a single module-level
`const`, and reuse that same instance and name throughout the file.

## 2. Name the logger by responsibility, not by trigger

Name the `source` string (and any bracket-text prefix in the message) after
the job the code does, not after how or when it's currently invoked.

- When a name candidate contains a trigger word (`Cron`, `Queue`, `Webhook`,
  `Endpoint`, `Job`), replace it with the responsibility it fulfills: e.g. a
  module that reconciles balances against a provider is `balanceReconciler`,
  not `balanceReconcilerCron`, regardless of whether it's currently invoked
  by a cron route, a queue consumer, or an admin endpoint.
- When two files sit at genuinely different responsibility layers — e.g. a
  raw API-client wrapper vs. the orchestrator that calls it and persists to a
  DB — give each its own name for its own job, rather than reusing one name
  for both just because a shared trigger-based name was dropped from both.
- Format: camelCase, no spaces/underscores/all-caps —
  `paymentWebhookHandler`, not `Payment Webhook Handler` /
  `payment_webhook_handler` / `PAYMENT_WEBHOOK_HANDLER`.

## 3. Log levels

| Level   | Use for |
|---|---|
| `debug` | Verbose diagnostics for local dev or targeted investigation. Must stay safe to enable in production without flooding logs. |
| `info`  | Normal operational events — one significant business action per line (a payment initiated, a card authorized, a webhook received). |
| `warn`  | Recoverable unexpected states — a retry succeeded, a fallback path was taken — worth investigating but not an active failure. |
| `error` | Unrecoverable failures or caught exceptions. Log the error object as the first field so the stack trace is captured. |

## 4. Fields object first, message last

The `jeeves-telemetry` (pino) logger takes the fields object first and the human-readable
message last — the message lands in `msg`, the fields land as queryable
top-level keys.

```typescript
// correct
logger.info({ cardId, companyId, amount }, 'Card authorization approved');
logger.error({ err, transactionId }, 'Settlement failed');

// incorrect
logger.info(`Card ${cardId} authorized for company ${companyId}`); // string concat — not queryable
logger.info('Card authorized', { cardId, companyId });             // args reversed
logger.info(cardId);                                               // primitive, not an object
```

## 5. Capture what makes a log line findable later

Every log line should carry the IDs someone will search by when debugging
this flow — the entity id, company/user id (if not already auto-injected),
external provider reference, batch/job id. Prefer these over free-text detail
buried in the message string. Check what your service's telemetry setup
already injects automatically (`source`, trace/span ids, user/company context
from CLS) and add only the fields it does not inject.

Keep field names consistent for the same concept across the whole service
(`transactionId`, not `txId` in one file and `transactionID` in another) —
consistent keys are what make cross-log search actually work.

## 6. One line per meaningful event

- Log once per significant state transition, not once per loop iteration or
  per retry attempt inside a tight loop — aggregate and log a summary instead
  (`{ processed, failed }`, not one line per item).
- A cron/sync job should log its start (with a run id) and its end (with a
  count/duration summary and per-item failures), not a line for every
  successful item — successes are implied by the summary; failures are what
  need their own line.

## 7. Redact sensitive data before it reaches the logger

Redact `req.body`, card/PAN/CVV data, tokens, API keys, and full user objects
before passing them to a logger:

- Strip a request body to its shape without its values — replace every
  non-ID string value recursively (keep IDs, drop everything else) — before
  logging it.
- Reduce a user/auth object down to just `{ userId, companyId }` before
  logging it.
- When redaction mutates its argument in place (deleting keys, masking values), pass a clone
  (e.g. `structuredClone(req.body)`) so downstream handlers still see the
  original, unredacted data.

## 8. Replace `console.*` entirely

`console.log/error/warn/info` produce unstructured output, break trace
correlation, and can't be filtered by level in the aggregator. Replace every
`console.*` call with the equivalent `logger` method on a `getLogger`-created
logger.

## 9. Time external calls and slow queries

Measure and log duration for any external API call or database query whose
latency could meaningfully vary — a third-party HTTP call, a multi-row
insert/update, a query over an unbounded or large result set.

- Capture the start with `performance.now()`, a monotonic clock immune to
  system-clock adjustments — `Date.now()` reads wall-clock time, which can
  jump backwards mid-measurement if the system clock gets corrected.
- Round the computed duration to a whole millisecond and log it under a
  `durationMs` key — the same key name every time is what makes cross-log
  search work.
- Attach the duration to the same log line as the call's success/failure
  outcome:
  ```typescript
  const start = performance.now();
  try {
    const result = await thirdPartyApi.fetch(params);
    logger.info(
      { durationMs: Math.round(performance.now() - start) },
      'Fetched from provider'
    );
    return result;
  } catch (err) {
    logger.error(
      { err, durationMs: Math.round(performance.now() - start) },
      'Provider fetch failed'
    );
    throw err;
  }
  ```
- For a batch of many individual calls (a loop, a chunked upsert), accumulate
  the per-call durations into one running total and log it once as a summary
  at the end of the batch, per rule 6.

## Reporting results

When reviewing how a service logs, report a table with columns
`File:line | Rule | Finding | Fix`, one row per violation, ordered by rule
number. Lead with a verdict line: the service and the count of violations. When
nothing violates a rule, say so in one line.
