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

## `audit_logs`

User and system actions in the accounting expense UI (filters, GL/category assignment, mapping and code changes) — answers "who changed a GL code or category, and when".

| Column | Type | Notes |
| --- | --- | --- |
| `id` | char(36) PK | |
| `companyId` | int unsigned | indexed |
| `userId` | varchar, nullable | indexed; always set in prod so far |
| `action` | varchar, nullable | indexed; `filters_used`, `auto_assigned_gl_category`, `gl_code_updated`, `category_assigned_to_transaction`, `gl_code_assigned_to_transaction`, `category_mapping_created`, `gl_code_created`, `tax_rate_created`, `merchant_mapping_created`, `merchant_mapping_updated`, `gl_code_upload`, `tax_rate_upload`, `export_expenses` |
| `featureType` | varchar, nullable | only `expense` seen |
| `flow` | varchar, nullable | `filter`, `categorization`, `import`, `export` |
| `integrationType` / `integrationPlatformReference` / `externalCompanyId` / `connectionId` / `accountId` | enum / varchar, nullable | all NULL in prod as of 2026-11 |
| `metaData` | json | keys vary by action: `filters_used` → `page`, `pageSize`, `posted`, `dateFrom`, `dateTo`, `rangeType`, `searchTerm`, `isZummaEnabled`; `auto_assigned_gl_category` → `glCode`, `glCodeId`, `macroCategoryId`, `transactionReferenceId`; `gl_code_updated` → `email` + `GLCode` or `taxRate`; `category_mapping_created` → `glCodeId`, `categoryId`, `createdBy` |
| `createdAt` / `updatedAt` / `deletedAt` | datetime(3) | UTC |

Action counts with metaData key sets:

```sql
SELECT action, JSON_KEYS(metaData) AS meta_keys, COUNT(*) AS n
FROM audit_logs
GROUP BY action, meta_keys
ORDER BY n DESC
```

## `company_accounting_categories`

A company's custom accounting fields (e.g. "Departments", "Centro de Costo"); the bulk import agent calls their values "categories". Answers "which companies have custom fields".

| Column | Type | Notes |
| --- | --- | --- |
| `id` | char(36) PK | the `category_id` the import agent receives when a file is uploaded from the field's page |
| `companyId` | int unsigned | |
| `name` | varchar(255) | field name shown in the UI |
| `status` | enum | `active`, `inactive` |
| `type` | enum | `DROPDOWN`, `FREE_TEXT`; default `DROPDOWN` |
| `showInAccounting` / `showInTransactions` / `isRequired` | tinyint(1) | |
| `createdAt` / `updatedAt` / `deletedAt` | datetime | paranoid, filter `deletedAt IS NULL` |

Companies with active dropdown fields:

```sql
SELECT companyId, COUNT(*) AS fields, GROUP_CONCAT(name SEPARATOR " | ") AS names
FROM company_accounting_categories
WHERE deletedAt IS NULL AND status = "active" AND type = "DROPDOWN"
GROUP BY companyId
```

## `company_accounting_category_options`

The values of a custom accounting field (`company_accounting_categories`), e.g. each cost center under "Centro de Costo". The bulk import agent's `category` items land here on approve.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | char(36) PK | |
| `companyAccountingCategoryId` | char(36) | FK `company_accounting_categories.id`; no `companyId` column, so join through the field |
| `name` | varchar(255) | value shown in the dropdown |
| `accountingCategoryOptionId` | varchar(255), nullable | the value's code (the import agent's `custom_id`); `NULL` when none was given |
| `status` | enum | `active`, `inactive` |
| `createdAt` / `updatedAt` / `deletedAt` | datetime | paranoid, filter `deletedAt IS NULL` |

Value count per custom field for a company:

```sql
SELECT c.name AS field, COUNT(o.id) AS options,
       SUM(o.accountingCategoryOptionId IS NOT NULL) AS withCode
FROM company_accounting_categories c
LEFT JOIN company_accounting_category_options o
  ON o.companyAccountingCategoryId = c.id AND o.deletedAt IS NULL
WHERE c.companyId = <companyId> AND c.deletedAt IS NULL
GROUP BY c.id, c.name
```
