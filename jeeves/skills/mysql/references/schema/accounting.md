# accounting (accounting-service)

| dev-NN | preprod | prod |
| --- | --- | --- |
| `accounting_<n>` (e.g. `accounting_20`) | `preprod_accounting` | `accounting` |

## `integration`

A company's accounting-platform connection (QBO / Xero / NetSuite via Codat), one row per connection.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | char(36), PK | uuid |
| `companyId` | int unsigned | backend `companies.id` |
| `externalCompanyId` / `externalCompanyName` | varchar(255) | the company as named in the accounting platform |
| `status` | enum | `pending`, `linked`, `unlinked`, `deauthorized`, `paused`; `linked` is an active integration |
| `type` | enum | `codat` |
| `platformName` | enum | `Codat QBO`, `Codat Xero`, `Codat NetSuite`, `Codat QBO Sandbox` |
| `platformReference` | enum | Codat platform key: `qhyg`, `gbol`, `akxx`, `ndsk`, `rvez` |
| `connectionId` / `connectionUrl` | varchar(255) | Codat connection, nullable |
| `linkedAt` / `unlinkedAt` | datetime(3) | nullable |
| `createdAt` / `updatedAt` / `deletedAt` | datetime(3) | filter `WHERE deletedAt IS NULL` for live rows |
| `platformCurrency` | varchar(255) | nullable |
| `errorMessage` | varchar(255) | nullable |
| `isConnectionTaxExclusive` | tinyint(1) | nullable |

Companies with integrations:

```sql
SELECT companyId, externalCompanyName, platformName, status, linkedAt
FROM integration
WHERE deletedAt IS NULL
ORDER BY companyId
```

Add `AND status = "linked"` for active integrations only.

## `transaction`

The transactions imported into accounting (Card Expenses, bill pay, transfers, fees). Each row comes from one report under `src/db/external-databases/sql/transaction-reports/`.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | char(36), PK | uuid |
| `companyId` | int unsigned | backend `companies.id` |
| `fundingSourceType` | enum | `SELF_FUNDED` (from `product_accounts_ledger` reports), `LOC` (from `loc-*` reports) |
| `transactionReferenceId` | varchar(255) | import dedup key. LOC card rows: `jeeves.transactions.uuid`. Self-funded card rows: `product_accounts_ledger.transactionReferenceId` (= `cards.card_transactions.id`). Self-funded fee rows: `cards.transaction_fees.id` |
| `tag` | enum | e.g. `cards`, `card-reversal-loc`, `card-refund-loc` (LOC); `card-purchase`, `card-reversal`, `card-refund`, `adjustment`, `iof-fee`, `bill-pay`, `self-funded-account-*` |
| `syncStatus` | enum | default `missing_categorization`; also `pending`, `processing`, `success`, `failed`, `categorized`, `attachment_upload_*` |
| `isExported` | tinyint(1) | `1` once exported to the ERP |
| `createdAt` / `updatedAt` / `deletedAt` | datetime(3) | soft delete via `deletedAt` |

SELF_FUNDED rows imported from dual-written LOC ledger rows (WAL-6448):

```sql
SELECT t.tag, t.syncStatus, t.isExported, COUNT(*) AS rows_, COUNT(DISTINCT t.companyId) AS companies
FROM accounting.transaction t
JOIN product_account.product_accounts_ledger pal
  ON pal.transactionReferenceId = t.transactionReferenceId
 AND pal.companyId = t.companyId
WHERE pal.source = "transactions"
  AND t.fundingSourceType = "SELF_FUNDED"
  AND t.deletedAt IS NULL
GROUP BY t.tag, t.syncStatus, t.isExported
```
