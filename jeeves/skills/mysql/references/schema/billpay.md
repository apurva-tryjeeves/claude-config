# billpay-service schema notes

| dev-NN | preprod | prod |
| --- | --- | --- |
| `billpay_<n>` | `preprod_billpay` | `billpay` |

## `invoices`

One row per bill-pay invoice / payout, including drafts.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | char(36) PK | |
| `companyId` | int unsigned | |
| `paymentSourceId` | varchar | wallet-funded payouts: `wallet_instruments.id` |
| `transactionAmount` / `transactionCurrency` | decimal(18,6) / smallint | `30840` = USDT |
| `baseCurrencyAmount` / `baseCurrency` | decimal / smallint | `20840` = USDC |
| `status` | enum | `draft`, `pending`, `scheduled`, `ready-to-initiate`, `initiated`, `in-review`, `payment-in-progress`, `completed`, `failed`, `canceled`, `archived`, … |
| `approvalStatus` | enum | `pending`, `in-review`, `approved`, `canceled`, `not-required` |

Open invoices for a company:

```sql
SELECT id, status, approvalStatus, transactionAmount, transactionCurrency, paymentSourceId, createdAt
FROM invoices
WHERE companyId = 31166 AND deletedAt IS NULL
  AND status NOT IN ("completed","canceled","archived","failed")
ORDER BY createdAt DESC
```

## `external_bills`

One row per bill imported from an external source; answers "did billpay receive the ERP bills".

- **Sources:** `ERP` (via ap-data-source-connector) and `SATWS`.
- **No `companyId`:** filter on `external_company_id`, the Codat company id (`integration.externalCompanyId` in accounting).

| Column | Type | Notes |
| --- | --- | --- |
| `id` | char(36) PK | |
| `external_bill_id` | char(36) | the ERP bill id |
| `external_company_id` | varchar | Codat company id |
| `source` | enum | `SATWS`, `ERP` |
| `status` | enum | source status: `Open`, `PartiallyPaid`, `Paid`, `Void`, `Draft`, `Unknown`, `VIGENTE`, `CANCELADO` |
| `jeeves_status` | enum | `draft`, `moved_to_payments`, `paid`, `payment_failed`, `pending_approval`, `canceled` |
| `vendor_id` | varchar | Jeeves vendor, nullable |
| `external_bill_invoice_number` / `external_vendor_name` | varchar | |
| `created_at` / `updated_at` | datetime | UTC |

ERP bills for one Codat company:

```sql
SELECT external_bill_id, external_bill_invoice_number, external_vendor_name, vendor_id,
       status, jeeves_status, source, created_at, updated_at
FROM external_bills
WHERE external_company_id = "0bae379d-3b50-4266-b1df-f335a38eb12e"
ORDER BY created_at
```
