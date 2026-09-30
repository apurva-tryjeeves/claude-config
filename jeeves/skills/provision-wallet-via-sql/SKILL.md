---
name: provision-wallet-via-sql
description: Provision a wallet for an org directly via SQL in a Jeeves dev env — the product account plus its wallet-instrument chain (instrument → provider account → linked bank account), all sharing one PK. Trigger when the user asks to create/add/seed/provision a wallet, wallet instrument, or product account for an org by SQL (e.g. "create a stablecoin wallet for org 2975 in dev-20").
---

# Provision Wallet via SQL

Seed a ready-to-use wallet for an org in a **dev** env: the wallet-instrument chain,
optionally with a new product account, chained by a shared PK.

| Env | Database names | Writes |
| --- | --- | --- |
| dev-01…dev-20 | `product_account_<n>`, `wallet_<n>`, `stablecoin_<n>` | Succeed |
| preprod, prod | — | Read-only |

## Read these first

- **Schema** → `references/wallet-schema.md` — the table chain and shared PK, wallet-type values, where each provider stores its identity, the stablecoin `providerAccountDetails` shape, and column enums.
- **DB access** → Skill `mysql` — the `jsql <env>/<service>` wrapper and the single-quoted multi-line form used here for anything longer than a short probe.

## Flow

Walk these in order, gathering answers before composing any query.

1. **Ask for the org** — `companyId` and env (e.g. dev-20).

2. **Ask: new or existing product account?**
   - **New** → generate a shared UUID; the flow inserts a `product_accounts` row. Ask the wallet type to fill `productType` / `baseCurrency` from the wallet-type table.
   - **Existing** → ask for the `productAccountId`; that id becomes the shared PK. Skip the `product_accounts` insert. Read its type so the instrument matches:
     ```bash
     jsql dev-NN/product_account '
     SELECT id, companyId, productType, baseCurrency
     FROM product_accounts
     WHERE id = "<productAccountId>"
     '
     ```

3. **Choose the provider** — show the full list and let the user pick:
   ```bash
   jsql dev-NN/wallet 'SELECT id, providerName FROM providers ORDER BY providerName'
   ```
   Use the chosen row's `id` as `providerId`.

4. **Fill the provider account identity** — this depends on the wallet type:
   - **Stablecoin (JSS)** → build `providerAccountDetails` from the matching wallet in `stablecoin_<n>`, following the shape in the schema reference, and confirm the values with the user. Skip the linked-bank-account insert.
   - **Fiat providers (Bridge, Qitech, Airwallex, …)** → confirm the bank details for the linked-bank-account row. Pull a real sample for that provider and ask if it's correct or needs editing:
     ```bash
     jsql dev-NN/wallet '
     SELECT lba.bankAccountDetails
     FROM wallet_instrument_provider_linked_bank_accounts lba
     JOIN wallet_instrument_provider_accounts pa
       ON pa.id = lba.walletInstrumentProviderAccountId
     WHERE pa.providerId = "<PROVIDER_ID>"
     ORDER BY lba.createdAt DESC
     LIMIT 1
     '
     ```
     Reuse it as-is, or apply the edits the user asks for.

5. **Summarize the ids, then show every composed query, gated on confirmation.** Group the ids under one bullet, `companyId` first:
   - Wallet
     - companyId: `<companyId>`
     - productAccountId / walletInstrumentId (shared PK): `<SHARED>`
     - providerId: `<PROVIDER_ID>`
     - providerAccountId (new): `<PROV_ACCT>`
     - linkedBankAccountId (new, fiat only): `<LINKED_BANK>`

   Then print the full INSERT set (below) with all values filled in. Run them only after the user confirms; otherwise apply their requested changes and show the summary + queries again.

## Queries to compose

Generate one shared UUID (or reuse the existing productAccountId) plus three fresh ones
(provider account, linked bank, external bank ref). Include the first INSERT only for a
**new** product account. Run each database's INSERTs through a quoted heredoc
(`jsql dev-NN/product_account <<'SQL'`, `jsql dev-NN/wallet <<'SQL'`) so the
single-quoted values and the JSON's double quotes pass through as written.

```sql
-- product_account_<n>  (NEW product account only)
INSERT INTO product_accounts
  (id, companyId, accountName, productType, baseCurrency, accountBalance, availableBalance,
   accountStatus, kycStatus, createdAt, updatedAt, createdBy, updatedBy, spendLimit,
   transactionBalance, collateralAmount, activatedAt)
VALUES ('<SHARED>', <companyId>, '<Account Name>', '<productType>', <baseCurrency>,
   0, 0, 'active', 'approved', NOW(3), NOW(3), '<createdBy>', '<createdBy>', 0, 0, 0, NOW(3));

-- wallet_<n>  (instrument reuses the shared PK)
INSERT INTO wallet_instruments
  (id, companyId, instrumentType, accountStatus, KYCStatus, baseCurrency, createdAt, updatedAt, createdBy, updatedBy)
VALUES ('<SHARED>', <companyId>, '<instrumentType>', 'active', 'approved', <baseCurrency>, NOW(3), NOW(3), '<createdBy>', '<createdBy>');

-- providerAccountDetails: stablecoin JSON for JSS, NULL for fiat
INSERT INTO wallet_instrument_provider_accounts
  (id, walletInstrumentId, providerId, providerAccountId, providerAccountDetails, createdAt, updatedAt, createdBy, updatedBy)
VALUES ('<PROV_ACCT>', '<SHARED>', '<PROVIDER_ID>', '<PROVIDER_ACCT_ID or NULL>', '<providerAccountDetails>', NOW(3), NOW(3), '<createdBy>', '<createdBy>');

-- Fiat providers only (Bridge, Qitech, Airwallex, …)
INSERT INTO wallet_instrument_provider_linked_bank_accounts
  (id, walletInstrumentProviderAccountId, providerLinkedBankAccountId, type, baseCurrency,
   bankAccountDetails, subType, status, createdAt, updatedAt, createdBy, updatedBy)
VALUES ('<LINKED_BANK>', '<PROV_ACCT>', '<PROV_LINKED>', 'topup', <bankCurrency>,
   '<bankAccountDetails JSON — confirmed in flow step 4>',
   'bankaccount', 'active', NOW(3), NOW(3), '<createdBy>', '<createdBy>');
```

## Verify & report

```bash
jsql dev-NN/product_account '
SELECT id, companyId, productType, accountStatus, kycStatus
FROM product_accounts
WHERE id = "<SHARED>"
'
```

```bash
jsql dev-NN/wallet '
SELECT id, companyId, instrumentType, accountStatus, KYCStatus
FROM wallet_instruments
WHERE id = "<SHARED>"
'
```

```bash
jsql dev-NN/wallet '
SELECT id, walletInstrumentId, providerId, providerAccountDetails
FROM wallet_instrument_provider_accounts
WHERE walletInstrumentId = "<SHARED>"
'
```

```bash
jsql dev-NN/wallet '
SELECT id, walletInstrumentProviderAccountId, type, status
FROM wallet_instrument_provider_linked_bank_accounts
WHERE walletInstrumentProviderAccountId = "<PROV_ACCT>"
'
```

Report the rows in a table with columns `Service | Table | Record` — one row per record — confirming the product account and wallet instrument share the PK.
- Status values (`accountStatus`, `kycStatus`, `KYCStatus`, `status`) carry an
  icon beside the value: ✅ `active`/`approved`, ⏳ `pending`/`in-review`/`rfi-*`,
  ⛔ `closed`/`deactivated`/`deleted`/`rejected`, ⚠️ `suspended`/`in-review-error`.
- Write every id in full — uuids and PKs stay untruncated.

Answer with the table, then stop. Follow `../../references/output-style.md` (plugin root)
for the shared reporting vocabulary.
