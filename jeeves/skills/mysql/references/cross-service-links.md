# Cross-service links

Logical relationships between tables in different service databases, held at
the application layer rather than a DB foreign key, since the tables live in
separate schemas.

Every service DB in a given env shares one MySQL host (confirmed: `develop-20`,
`preprod`, `prod` each resolve to a single host across all their service DBs),
so a cross-service query can be written as a single same-host, cross-schema
`JOIN`:

```sql
SELECT ...
FROM wallet_20.wallet_instrument_top_ups w
JOIN stablecoin_20.stablecoin_deposits s ON ...
```

Populate this file incrementally: append a section the first time a
cross-service query is worked out. Format:

```markdown
## <short name for the relationship>

- <service>.<table>.<column>  ↔  <service>.<table>.<column>
- Match on: <the actual join condition — e.g. a shared reference ID, not an
  enforced FK>
- Direction / lag: <which side is written first, whether there's async delay,
  whether the relationship is 1:1 or 1:many>
- Query pattern: <the cross-schema JOIN, or note if this env's services are on
  separate hosts and it needs two `jsql` calls instead>
```

## Dual-written LOC ledger row ↔ accounting transaction

- `product_account.product_accounts_ledger.transactionReferenceId` ↔ `accounting.transaction.transactionReferenceId`, filtered to `pal.source = "transactions"`
- Card spends: `pal.transactionReferenceId` = `cards.card_transactions.id` = `jeeves.transactions.syncKey`. The LOC accounting row to keep has `transactionReferenceId = jeeves.transactions.uuid`, and the SELF_FUNDED row is the duplicate
- Card refunds whose `jeeves.transactions.transactionStatus = "refunded"` have no LOC accounting row, since `loc-card-transactions.sql` imports `completed` only
- Adjustments: `pal.transactionReferenceId` = `jeeves.transactions.uuid`, so LOC and SELF_FUNDED share one reference id. Accounting holds a single row
- Card fees: `accounting.transaction.transactionReferenceId` = `cards.transaction_fees.id`, and `transaction_fees.transactionId` = `pal.transactionReferenceId`
- Query pattern: one cross-schema `JOIN` on prod. `jeeves.transactions.syncKey` has no index (13M rows), so a bare `syncKey` join loses the connection (`ERROR 2013`). Join on `jt.companyId = <companyId> AND jt.syncKey = <id>` to use the `companyId` indexes, and run it in the background

## Wallet ↔ product account ↔ bill-pay invoice

- `wallet.wallet_instruments.id` ↔ `product_account.product_accounts.id` ↔ `billpay.invoices.paymentSourceId`
- Match on: the shared id (one PK across all three)
- Direction / lag: wallet ledger rows settle first; `product_accounts.accountBalance` reflects the settled `wallet_transactions` sum
- Query pattern: same-host cross-schema `JOIN` on prod, or one `jsql` call per database
