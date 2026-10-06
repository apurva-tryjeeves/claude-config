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
