# Wallet Schema (dev envs)

How a wallet is stored across the product-account and wallet databases. Substitute
the env number for `<n>` (dev-20 → `product_account_20`, `wallet_20`).

## Table chain

```
product_account_<n>.product_accounts                              (id = PK)
wallet_<n>.wallet_instruments                                     (id = same PK)
        └─ wallet_instrument_provider_accounts                    (walletInstrumentId → PK)
                └─ wallet_instrument_provider_linked_bank_accounts (walletInstrumentProviderAccountId → provider account id)
```

- `product_accounts.id` and `wallet_instruments.id` are the **same UUID** — the code joins on equal PKs.
- The provider account and linked bank account each get a fresh UUID.
- Providers live in `wallet_<n>.providers` (`id`, `providerName`); the provider account's `providerId` points there.

## Wallet-type values

| Wallet type          | `productType`         | `instrumentType`      | wallet `baseCurrency` | bank `baseCurrency` |
| -------------------- | --------------------- | --------------------- | --------------------- | ------------------- |
| Stablecoin (USDC)    | `stablecoin`          | `stablecoin`          | `10840`               | `840` (USD)         |
| Self-funded          | `self-funded`         | `self-funded`         | ISO numeric           | matching ISO        |
| Jeeves Pay external  | `jeeves-pay-external` | `jeeves-pay-external` | ISO numeric           | matching ISO        |

`createdBy` / `updatedBy` = user email or `system@tryjeeves.com`.

## Where the provider identity lives

| Wallet type | Identity column | Linked bank account row |
| --- | --- | --- |
| Stablecoin (JSS) | `wallet_instrument_provider_accounts.providerAccountDetails` | None |
| Fiat (Bridge, Qitech, Airwallex, …) | `wallet_instrument_provider_linked_bank_accounts.bankAccountDetails` | One `topup` row; add a `withdrawal` row when needed. `providerAccountDetails` = `NULL` |

### Stablecoin `providerAccountDetails`

Keyed under `stablecoin`. The wallet service reads `providerAccountDetails.stablecoin.wallet.id`,
`.address`, `.customerId`, and `.paymentRail` directly, so populate all four:

```json
{"stablecoin":{"wallet":{"id":"<stablecoin wallet uuid>"},"address":"<on-chain address>","customerId":"<stablecoin customer uuid>","paymentRail":"solana"}}
```

Source the values from the matching wallet in `stablecoin_<n>`:

| Field | Source |
| --- | --- |
| `wallet.id` | stablecoin-service wallet id |
| `customerId` | that wallet's customer id |
| `address` | on-chain deposit address |
| `paymentRail` | e.g. `solana` |

## Enums

| Table | Column | Values |
| --- | --- | --- |
| `product_accounts` | `accountStatus` | `pending` / `closed` / `active` / `deactivate` / `archived` |
| `product_accounts` | `kycStatus` | `approved` / `pending` / `in-review` / `in-jeeves-review` / `in-review-error` / `rejected` / `rfi-required` / `rfi-answered` / `rfi-closed` |
| `wallet_instruments` | `accountStatus` | `pending` / `active` / `deactivated` / `closed` |
| `wallet_instruments` | `KYCStatus` | `approved` / `pending` / `in-review` / `suspended` / `rejected` / `rfi-*` |
| `wallet_instrument_provider_linked_bank_accounts` | `type` | `topup` / `withdrawal` |
| `wallet_instrument_provider_linked_bank_accounts` | `subType` | `bankaccount` / `brl-pix` |
| `wallet_instrument_provider_linked_bank_accounts` | `status` | `active` / `pending` / `deactivated` / `deleted` |
