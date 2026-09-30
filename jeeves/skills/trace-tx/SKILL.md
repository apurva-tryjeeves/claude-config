---
name: trace-tx
description: Trace one JeevesInc transaction end to end — its rows in the wallet, transactions and product-account databases plus the matching application logs — and return a single chronological timeline. Trigger when the user gives a transaction UUID and asks what happened to it, where it is stuck, or why it failed.
---

# Trace a Transaction

Trace one transaction across Jeeves services and produce a single chronological
timeline.

| Environment | DB access | Logs |
| --- | --- | --- |
| prod | `jsql prod/<database> '<sql>'` | `mcp__opensearch-prod__*` |
| preprod | `jsql preprod/<database> '<sql>'` | `mcp__opensearch-dev__*` |
| dev-01…dev-20 | `jsql dev-NN/<service> '<sql>'` | `mcp__opensearch-dev__*` |

- **Read-only throughout** — keep every query a `SELECT`.
- **DB rules** → Skill `mysql`, for the wrapper and per-service database selection.
- **Log rules** → Skill `opensearch`, for indices, fields and query patterns.
- **Column names** → read `mysql`'s `references/schema/<service>.md` before
  composing a query, and append what you discover there in the same turn.
- **Expired credentials** — prod log queries returning empty or unauthorized
  usually mean a stale SSO session:
  ```bash
  aws sso login --profile jeeves_dev
  ```

## Establish the inputs
- **Transaction id** — usually a UUID, taken from the request. Ask for it when none is given.
- **Environment** — `dev-NN`, `preprod` or `prod`. When the request names one, use it for every query; otherwise ask via `AskUserQuestion`, offering the workspace repos' envs first.
- **Target** — on dev, name the service (`dev-20/wallet`); the wrapper appends the env number. On preprod and prod, name the full database.

## Gather (query each in parallel where possible)
1. **wallet_<n>** — the wallet transaction and its sub-transactions, provider references, and status. Search by the id, then by any provider reference ids that turn up.
2. **transactions_<n>** — the universal transaction row(s) and status history tied to this id.
3. **product_account_<n>** — related ledger entries and balance movements.
4. **Logs** — `match_phrase` the id in the `log` field over a sensible `@timestamp` window (widen it when empty), scoped by `app_name.keyword` to the wallet, transaction and product-account services. Use the MCP server for the env from the table above. Surface errors and webhook receipts.

## Report
Icons, linking and value-rendering vocabulary live in the shared
`../../references/output-style.md` — follow it rather than inventing a format.

Present one chronological timeline: created → wallet-transaction-engine →
provider integration → webhook receipt → status propagation → ledger entries.
Give each step its key ids, status, amount and currency, timestamp, and
provider. Call out explicitly:

- a status or amount mismatch between services,
- a missing leg — a webhook with no prior initiation, a ledger entry with no transaction,
- anything sitting in a non-terminal state.

Keep it to the timeline or a table rather than raw row dumps. Say plainly when
a service holds no row for the id. Answer with the timeline, then stop — leave
out the queries run and "want me to check another service?" follow-ups.
