# Review checklist

Read the change for what breaks in production and what it costs to change later. Order findings by severity.

| Severity | Meaning |
|---|---|
| Blocker | Data loss, security hole, wrong money or state, outage risk |
| Major | Incorrect behaviour in a reachable case, missing failure handling, a design that blocks the next change |
| Minor | Readability, naming, structure, test gaps with low risk |

## Design review

- Requirements carry numbers, and the design meets them.
- Each table has one owner; migrations deploy in reversible steps.
- Every write is safe to retry; every consumer handles a duplicate.
- Each outbound call has a timeout, a retry policy and a degraded behaviour.
- Authorization and tenant isolation are stated per endpoint.
- Rollout and rollback are written down.
- A simpler design that meets the same numbers has been considered and the choice explained.

## Code review

1. **Correctness:** edge cases, empty and maximum inputs, concurrency, time zones, rounding of money.
2. **Failure paths:** errors handled or propagated with context; partial failure leaves consistent state.
3. **Security:** input validated at the boundary; authorization per resource; tenant in every query; secrets and personal data out of logs.
4. **Data:** indexes for new queries, bounded result sets, short transactions, queries batched.
5. **Types:** illegal states unrepresentable; `any` and casts replaced or justified; exhaustive handling of unions.
6. **Structure:** module boundaries respected; dependencies point inward; one reason to change per module.
7. **Judgement test:** each advanced construct earns its place; each pattern removes a named problem; plain code elsewhere.
8. **Runtime:** event loop kept free; concurrency bounded; cancellation passed through; resources released.
9. **React:** state in the right place; effects only for external sync; the four view states; accessibility.
10. **Tests:** cover the behaviour and the main failure path; deterministic.
11. **Operability:** logs, metrics and alerts for the new path; a flag or a rollback step.

## Finding format

`<severity> — <file>:<line> — <what fails and when> — <the fix>`

Give the reason with each finding. State what you verified by running it and what you read only.
