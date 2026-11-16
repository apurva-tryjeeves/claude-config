# transactions — schema notes

Database names per env: the service table in `SKILL.md` ("Default").

## `ut_transactions`

The universal transaction row for a transaction; answers "what is this transaction's status across services". Columns are snake_case, unlike the wallet and product_account databases.

| Column | Type | Notes |
| --- | --- | --- |
| `uuid` | | the transaction UUID; match a transaction id here |
| `transaction_reference_id` | | shared reference id; equals `wallet_transactions.transactionReferenceId` |
| `parent_transaction_reference_id` | | parent's reference id; equals `wallet_transactions.parentTransactionReferenceId` |
| `transaction_status` | | externally visible status |
| `internal_transaction_status` | | internal status |
| `failure_reason` | | set when the transaction failed |

Join keys: `ut_transactions.transaction_reference_id` → `wallet_transactions.transactionReferenceId`, `product_accounts_ledger.transactionReferenceId`

```sql
SELECT uuid, transaction_status, internal_transaction_status, failure_reason
FROM ut_transactions
WHERE uuid = "<id>" OR transaction_reference_id = "<id>" OR parent_transaction_reference_id = "<id>";
```
