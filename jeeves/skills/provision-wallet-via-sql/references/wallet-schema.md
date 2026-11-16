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

| Wallet type | `productType` / `instrumentType` | wallet `baseCurrency` | `product_accounts.metadata` | linked row `baseCurrency` |
| --- | --- | --- | --- | --- |
| Stablecoin USDC (JSS) | `crypto-wallet` | `20840` | `{"provider":"jss"}` | `20840` |
| Stablecoin USDT (JSS) | `crypto-wallet` | `30840` | `{"provider":"jss"}` | `30840` |
| Self-funded | `self-funded` | ISO numeric | `NULL` | matching ISO |
| Jeeves Pay external | `jeeves-pay-external` | ISO numeric | `NULL` | matching ISO |

`10840` is USDB, not USDC. The `stablecoin` enum value exists but the code
never creates it — use `crypto-wallet` for every JSS wallet.

`createdBy` / `updatedBy` = user email or `system@tryjeeves.com`.

## Where the provider identity lives

| Wallet type | `providerAccountId` | `providerAccountDetails` | Linked bank account rows |
| --- | --- | --- | --- |
| Stablecoin (JSS) | the stablecoin customer id | `jss` shape below | One `topup` row per chain the wallet receives on — deposits fail with `No linked bank account found … on chain` without it |
| Fiat (Bridge, Qitech, Airwallex, STP, …) | copy the shape of a real row for that provider | keyed by the provider (`airwallex`, `stp`, `qitech`, `bridge`) plus `accountStatus` — copy a real sample (only dLocal rows are `NULL`) | One `topup` row; add a `withdrawal` row when needed |

### JSS `providerAccountDetails`

The wallet service reads `providerAccountDetails.jss.*`:

```json
{"jss":{"wallet":{"id":"<stablecoin_wallets.id>"},"customerId":"<stablecoin_wallets.customerId>","paymentRail":"<stablecoin_wallets.chain>"},"accountStatus":"ACTIVE"}
```

| Field | Source |
| --- | --- |
| `jss.wallet.id` | `stablecoin_<n>.stablecoin_wallets.id` |
| `jss.customerId` | that wallet's `customerId` — also the provider account's `providerAccountId` |
| `jss.paymentRail` | that wallet's `chain` (e.g. `tron`, `solana`, `tempo`) |

### JSS linked bank account (`topup`, one per chain)

`providerLinkedBankAccountId` is the deposit address's id, and
`bankAccountDetails` carries the address:

```json
{"currency":20840,"bankCountry":"","accountNumber":"<address>","stablecoinDepositAddress":{"id":"<deposit address id>","chain":"<chain>","address":"<address>","currency":"USDC","walletId":"<stablecoin_wallets.id>"}}
```

The deposit address and its id come from the stablecoin provider and are not
stored in `stablecoin_<n>` — take them from the user, or from an existing
linked row for the same wallet.

## Enums

Enum values live in the mysql schema notes: `jeeves:mysql` `references/schema/wallet.md` (`wallet_instruments`, `wallet_instrument_provider_linked_bank_accounts`) and `references/schema/product_account.md` (`product_accounts`).
