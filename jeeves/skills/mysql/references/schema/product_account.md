# product_account (product-account-service)

Database names per env: the service table in `SKILL.md` ("Default").

## `product_accounts_ledger`

One row per product-account ledger movement (card spend, fee, deposit, adjustment). The self-funded import reports read it.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | char(36), PK | uuid |
| `productAccountId` | char(36) | |
| `transactionReferenceId` | varchar(255), unique | card rows: `cards.card_transactions.id`; adjustment rows written from LOC: `jeeves.transactions.uuid` |
| `companyId` | int unsigned | |
| `transactionTypeTag` | enum | `card-purchase`, `card-reversal`, `card-refund`, `adjustment`, `iof-fee`, `bill-pay`, `self-funded-account-*`, … |
| `transactionStatus` | enum | `pending`, `failed`, `settled` |
| `parentTransactionReferenceId` | varchar(255) | set on child rows (fees) |
| `source` | varchar(64) | default `product_accounts_ledger` (native); `transactions` = dual-written from `jeeves.transactions` when `ENABLE_LOC_PA_LEDGER` is on |
| `createdAt` / `updatedAt` / `deletedAt` | datetime(3) | |

Dual-written LOC rows for a company:

```sql
SELECT transactionTypeTag, transactionStatus, COUNT(*)
FROM product_accounts_ledger
WHERE source = "transactions" AND companyId = 8865
GROUP BY transactionTypeTag, transactionStatus
```

## `product_accounts`

One row per product account; holds the live balance. `id` is shared with `wallet.wallet_instruments.id`.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | char(36), PK | = `wallet_instruments.id` |
| `companyId` | int unsigned | |
| `productType` | enum | `self-funded`, `jeeves-pay-external`, `jeeves-pay-credit`, `crypto-wallet`, `credit-line`, `stablecoin` |
| `baseCurrency` | smallint | `20840` = USDC |
| `accountBalance` / `availableBalance` | decimal(30,6) | |
| `accountStatus` | enum | `pending`, `closed`, `active`, `deactivate`, `archived` |
| `kycStatus` | enum | `approved`, `pending`, `in-review`, `in-jeeves-review`, `in-review-error`, `rejected`, `rfi-required`, `rfi-answered`, `rfi-closed` |

```sql
SELECT id, productType, baseCurrency, accountBalance, availableBalance, accountStatus, updatedAt
FROM product_accounts
WHERE companyId = 31166 AND deletedAt IS NULL
```
