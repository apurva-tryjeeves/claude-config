# accounting (accounting-service)

Database names per env: the service table in `SKILL.md` ("Default").

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

## `transaction_gl_codes`

A company's GL accounts, synced from the ERP (`isExternal = 1`) or created in Jeeves. Answers "which GL codes does this integration have".

| Column | Type | Notes |
| --- | --- | --- |
| `id` | char(36) PK | |
| `companyId` | int unsigned | |
| `integrationId` | char(36), nullable | FK `integration.id` |
| `code` / `nominalCode` / `name` | varchar | unique per (`companyId`, `integrationId`, `code`) |
| `accountType` | enum | GL account type |
| `isExternal` / `isDisabled` / `isArchived` | tinyint(1) | |
| `sourceModifiedDate` / `createdAt` / `updatedAt` / `deletedAt` | datetime(3) | UTC; paranoid, filter `deletedAt IS NULL` |

GL codes shared by two integrations (same ERP organisation behind both):

```sql
SELECT COUNT(*) AS sharedCodes, SUM(a.name = b.name) AS sameName
FROM transaction_gl_codes a
JOIN transaction_gl_codes b ON b.code = a.code
WHERE a.integrationId = "<integration A>" AND a.deletedAt IS NULL
  AND b.integrationId = "<integration B>" AND b.deletedAt IS NULL
```

## `company_tax_rates`

A company's tax rates, synced from the ERP or created in Jeeves.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | char(36) PK | |
| `companyId` | int unsigned | |
| `integrationId` | char(36), nullable | FK `integration.id` |
| `name` / `code` / `displayName` | varchar | |
| `externalTaxRateId` | varchar, nullable | the ERP's tax-rate id; join key across integrations |
| `totalTaxRate` / `effectiveTaxRate` | decimal | |
| `isExternal` / `isDisabled` / `isArchived` | tinyint(1) | |
| `createdAt` / `updatedAt` / `deletedAt` | datetime | UTC |

Per-integration summary:

```sql
SELECT integrationId, COUNT(*) AS total, SUM(deletedAt IS NULL) AS live, MAX(createdAt) AS lastCreated
FROM company_tax_rates
WHERE integrationId IN ("<integration A>", "<integration B>")
GROUP BY integrationId
```

## `supplier`

ERP suppliers (vendors) synced per integration, plus suppliers Jeeves pushed to the ERP.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | char(36) PK | |
| `companyId` | int unsigned, nullable | |
| `integrationId` | char(36), nullable | FK `integration.id` |
| `accountId` | char(36), nullable | FK `account.id` |
| `externalSupplierId` | varchar, nullable | the ERP contact id; join key across integrations |
| `name` / `contactName` / `currency` / `emailAddress` / `phone` | varchar | |
| `status` / `syncStatus` / `pushOperationStatus` | enum | |
| `isActive` | tinyint(1) | |
| `sourceModifiedDate` / `createdAt` / `updatedAt` / `deletedAt` | datetime(3) | UTC |

Suppliers shared by two integrations:

```sql
SELECT COUNT(*) AS sharedSuppliers, SUM(a.name = b.name) AS sameName
FROM supplier a
JOIN supplier b ON b.externalSupplierId = a.externalSupplierId
WHERE a.integrationId = "<integration A>" AND a.deletedAt IS NULL
  AND b.integrationId = "<integration B>" AND b.deletedAt IS NULL
```
