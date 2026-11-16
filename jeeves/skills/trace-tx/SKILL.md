---
name: trace-tx
description: Trace one JeevesInc transaction end to end — its rows in the wallet, transactions and product-account databases plus the matching application logs — and return a single chronological timeline. Trigger when the user gives a transaction UUID and asks what happened to it, where it is stuck, or why it failed.
---

# Trace a Transaction

Trace one transaction across Jeeves services and produce a single chronological
timeline. For a batch, sync or trace id, search the logs with `jeeves:opensearch`.

| Environment | Wallet / transactions / product-account databases | Logs |
| --- | --- | --- |
| prod | `jsql prod/wallet`, `prod/transactions`, `prod/product_account` | `mcp__opensearch-prod__*` |
| preprod | `jsql preprod/preprod_wallet`, `preprod/preprod_transactions`, `preprod/preprod_product_account` | `mcp__opensearch-dev__*` |
| dev-01…dev-20 | `jsql dev-NN/wallet`, `dev-NN/transactions`, `dev-NN/product_account` | `mcp__opensearch-dev__*` |

- **Read-only throughout** — keep every query a `SELECT`.
- **DB rules** → Skill `jeeves:mysql`, for the wrapper and per-service database selection.
- **Log rules** → Skill `jeeves:opensearch`, for indices, fields and query patterns.
- **Column names** → read `jeeves:mysql`'s `references/schema/<service>.md`
  (`wallet.md`, `product_account.md`) before composing a query, and record
  what you discover following `${CLAUDE_PLUGIN_ROOT}/references/write-back.md`.
- **Reusable queries** → `${CLAUDE_PLUGIN_ROOT}/references/queries.md` — read it when the user
  refers to a saved query.
- **Expired credentials** — an auth error from a log or DB query means a
  stale SSO session; log in as `jeeves:aws-secrets` "Authentication" describes. An empty result is a
  finding: widen the window first.

## Establish the inputs
- **Transaction id** — usually a UUID, taken from the request. Ask for it when none is given.
- **Environment** — `dev-NN`, `preprod` or `prod`. When the request names one, use it for every query. Otherwise ask via `AskUserQuestion` with four options: `prod`, `preprod`, the dev-NN named earlier in the conversation (or `dev-20`), and "Other dev env". On "Other dev env", ask in plain text for the number.
- **Target** — use the database names from the table above for every query.

## Gather (query each in parallel where possible)
The id usually matches on `id` or on the transaction reference id, which all three databases carry:

| Database | Table | Match the id on | Also read |
| --- | --- | --- | --- |
| wallet | `wallet_transactions` | `id`, `transactionReferenceId`, `parentTransactionReferenceId` | `walletInstrumentId`, `transactionTypeTag`, `transactionStatus`, amounts |
| wallet | `wallet_sub_transactions` | `walletTransactionId` = `wallet_transactions.id` | `sourceType`, `destinationType`, `transactionStatus`, `providerTransactionReferenceId`, `failureInfo` |
| transactions | `ut_transactions` (columns in `jeeves:mysql` `references/schema/transactions.md`) | `uuid`, `transaction_reference_id`, `parent_transaction_reference_id` | status and failure columns per that note |
| product_account | `product_accounts_ledger` | `transactionReferenceId`, `parentTransactionReferenceId` | `productAccountId`, `transactionStatus`, `internalTransactionStatus`, `failureReason` |

1. **wallet** — the wallet transaction and its sub-transactions, provider references, and status. Search by the id, then by any provider reference ids that turn up.
2. **transactions** — the universal transaction row(s) in `ut_transactions` tied to this id.
3. **product_account** — related ledger entries in `product_accounts_ledger`.
4. **Logs** — `match_phrase` the id in the `log` field over a sensible `@timestamp` window (widen it when empty), with no `app_name.keyword` filter, so the id match returns every service it touched; scope by an `app_name.keyword` seen in those hits when the volume is high. Use the MCP server for the env from the table above. Surface errors and webhook receipts.

## Reporting results
Icons, linking and value-rendering vocabulary live in the shared
`${CLAUDE_PLUGIN_ROOT}/references/output-style.md` — follow it rather than inventing a format.

Present one chronological timeline: created (`wallet_transactions`) → provider
integration (`wallet_sub_transactions`, provider log lines) → webhook receipt
(log lines) → status propagation (`ut_transactions`) → ledger entries
(`product_accounts_ledger`).
Give each step its key ids, status, amount and currency, timestamp, and
provider. Call out explicitly:

- a status or amount mismatch between services,
- a missing leg — a webhook with no prior initiation, a ledger entry with no transaction,
- anything sitting in a non-terminal state.

Keep it to the timeline or a table rather than raw row dumps. Say plainly when
a service holds no row for the id. Answer with the timeline, then stop — leave
out the queries run and "want me to check another service?" follow-ups.
