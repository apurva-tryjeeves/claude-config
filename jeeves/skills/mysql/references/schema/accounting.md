# accounting (accounting-service)

Dev/preprod database: `accounting_<n>` (e.g. `accounting_20`).

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
ORDER BY companyId;
```

Add `AND status = 'linked'` for active integrations only.
