# wallet-service schema notes

| dev-NN | preprod | prod |
| --- | --- | --- |
| `wallet_<n>` | `preprod_wallet` | `wallet` |

## `wallet_instruments`

One row per customer wallet. `id` is shared with `product_account.product_accounts.id`.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | char(36) PK | = `product_accounts.id` = `billpay.invoices.paymentSourceId` |
| `companyId` | int unsigned | |
| `instrumentType` | enum | `self-funded`, `jeeves-pay-external`, `crypto-wallet`, `stablecoin` |
| `accountStatus` | enum | `pending`, `active`, `deactivated`, `closed` |
| `baseCurrency` | smallint | ISO numeric; `20840` = USDC, `170` = COP |

```sql
SELECT id, instrumentType, accountStatus, baseCurrency, createdAt
FROM wallet_instruments
WHERE companyId = 31166
```

## `wallet_transactions`

One row per ledger-facing wallet movement (deposit, fee, bill-pay). Fee rows hang off their deposit via `parentTransactionReferenceId`.

| Column | Type | Notes |
| --- | --- | --- |
| `walletInstrumentId` | char(36) | → `wallet_instruments.id` |
| `transactionType` | enum | `credit`, `debit` |
| `transactionStatus` | enum | `pending`, `in-review`, `failed`, `settled` |
| `transactionTypeTag` | enum | `self-funded-account-deposit`, `self-funded-account-deposit-fee`, `self-funded-account-deposit-delta`, `bill-pay`, `adjustment`, … |
| `baseCurrencyAmount` | decimal(30,6) | amount credited/debited to the product-account ledger |
| `transactionAmount` | decimal(30,6) | source-currency amount (COP for PSE deposits) |
| `transactionReferenceId` | char(36), unique | Bridge transfer id for Bridge deposits |
| `parentTransactionReferenceId` | char(36) | fee row → deposit's `transactionReferenceId` |

Settled balance per wallet, by tag:

```sql
SELECT transactionTypeTag, transactionType, transactionStatus,
       COUNT(*) AS n, ROUND(SUM(baseCurrencyAmount),2) AS total
FROM wallet_transactions
WHERE walletInstrumentId = "<walletInstrumentId>" AND deletedAt IS NULL
GROUP BY transactionTypeTag, transactionType, transactionStatus
```

## `wallet_sub_transactions`

The actual money movements behind a `wallet_transactions` row (sweeps, treasury top-ups).

| Column | Type | Notes |
| --- | --- | --- |
| `walletTransactionId` | char(36) | → `wallet_transactions.id` |
| `sourceType` / `destinationType` | enum | `self-funded`, `provider-treasury-account`, `external-bank`, `crypto-beneficiary`, … |
| `baseCurrencyAmount` | decimal(30,6) | Jeeves-side amount |
| `providerTransactionAmount` | decimal(30,6) | amount actually sent to the provider (fee sweep = fee ± `feeAdjustmentAmount`) |
| `transactionStatus` | enum | `settled`, `settled-with-no-money-movement`, `ready-to-initiate`, `failed`, … |
| `providerTransactionReferenceId` | varchar | Bridge transfer id of the movement |
| `metadata` | json | `feeAdjustmentType` (`credit`/`debit`), `feeAdjustmentAmount` on deposit-fee sweeps |

Money that actually moved on a wallet, by direction:

```sql
SELECT t.transactionTypeTag, s.sourceType, s.destinationType, s.transactionStatus, COUNT(*) AS n,
       ROUND(SUM(t.baseCurrencyAmount),2) AS ledgerAmt,
       ROUND(SUM(s.baseCurrencyAmount),2) AS subAmt,
       ROUND(SUM(s.providerTransactionAmount),2) AS providerAmt
FROM wallet_transactions t
JOIN wallet_sub_transactions s ON s.walletTransactionId = t.id
WHERE t.walletInstrumentId = "<walletInstrumentId>" AND t.transactionStatus = "settled"
GROUP BY t.transactionTypeTag, s.sourceType, s.destinationType, s.transactionStatus
```

## `bridge_pse_onramp_transfers`

One row per PSE (Colombia COP) on-ramp link. Holds only the COP amount; the USD quote lives on the pending deposit in `wallet_transactions`.

| Column | Type | Notes |
| --- | --- | --- |
| `walletInstrumentId` | char(36) | |
| `bridgeTransferId` | varchar, unique | = `wallet_transactions.transactionReferenceId` of the deposit |
| `amount` | varchar | COP |
| `status` | enum | `initiated`, `pending`, `completed`, `failed` |
