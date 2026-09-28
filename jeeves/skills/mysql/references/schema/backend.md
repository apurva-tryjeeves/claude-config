# backend (monolith / "jeeves")

Dev/preprod database: `develop_<n>` (e.g. `develop_01`). **Prod database name differs from the `_<n>` convention: it's just `jeeves`.**

## `exchange_rates`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | int unsigned, PK, auto_increment | |
| `uuid` | char(36) | nullable |
| `sourceCurrency` | smallint unsigned | numeric currency code, FK to `currency_lookup.numericCode` |
| `destinationCurrency` | smallint unsigned | numeric currency code |
| `rates` | decimal(12,6) | rate: 1 unit of source currency = `rates` units of destination currency |
| `invertedRate` | decimal(12,6) | |
| `destinationCurrencyAlphaCode` | char(4) | alpha code stored directly on the row (unlike source, which only has the numeric code) |
| `createdAt` / `updatedAt` / `deletedAt` | datetime | `deletedAt` nullable, filter `WHERE deletedAt IS NULL` for live rows |
| `metadata` | json | |

No single-latest-row constraint — the table is append-only history per pair. To get the latest rate per `(sourceCurrency, destinationCurrencyAlphaCode)` pair, window-function pattern:

```sql
WITH ranked AS (
  SELECT er.sourceCurrency, cl.alphaCode AS sourceAlphaCode, er.destinationCurrencyAlphaCode,
         er.rates, er.createdAt,
         ROW_NUMBER() OVER (PARTITION BY er.sourceCurrency, er.destinationCurrencyAlphaCode
                             ORDER BY er.createdAt DESC) AS rn
  FROM exchange_rates er
  JOIN currency_lookup cl ON cl.numericCode = er.sourceCurrency
  WHERE er.deletedAt IS NULL
)
SELECT sourceAlphaCode, destinationCurrencyAlphaCode, rates, createdAt
FROM ranked
WHERE rn = 1 AND sourceAlphaCode = 'USD'
ORDER BY destinationCurrencyAlphaCode;
```

Note: rows are historical snapshots from whenever a cron last wrote them — some pairs (e.g. USD->ARS) can be years stale, since the value only updates when that cron actually runs for that pair. Not a live/current-rate source, treat as "last known" only.

`USDT` is not directly quoted against `USD` in this table as of this writing (no `sourceAlphaCode='USD' AND destinationCurrencyAlphaCode='USDT'` row found) — Bitso quotes crypto pairs via its own book format (`usd_usdt`), separate from the apilayer-style rows here. `MXN/EUR/BRL/EURC -> USDT` rows do exist (written by the USDT triangulation cron, per `backend`'s `modules/exchangeRate/bitso/usdtTriangulationCronService.js`).

## `currency_lookup`

| Column | Type | Notes |
| --- | --- | --- |
| `numericCode` | smallint unsigned, PK | e.g. `840` = USD |
| `currency` | varchar(255) | display name, e.g. "US Dollar" |
| `alphaCode` | char(4) | e.g. "USD" |
| `isDisplay` | tinyint(1) | |
| `isPaymentCurrency` | tinyint(1) | |

Used to resolve `exchange_rates.sourceCurrency` (numeric) to an alpha code via `JOIN currency_lookup cl ON cl.numericCode = er.sourceCurrency`.

## `multifactor_action_code`

Holds MFA/OTP codes for actions like login — this is where a dev-env login OTP
lives when email delivery isn't configured/checked (retrieve it directly
instead of waiting on an email).

| Column | Type | Notes |
| --- | --- | --- |
| `id` | bigint unsigned, PK, auto_increment | |
| `userId` | int unsigned | FK to the user | 
| `code` | varchar(255) | the OTP/code itself, e.g. `'122045'` |
| `actionType` | varchar(255) | e.g. `USER_LOGIN` |
| `status` | enum | `active`, `completed`, `expired`, `revoked`, `pending` — only `active` codes are still usable |
| `notificationType` | enum | `email`, `sms`, `otp`, `mobile-app`, `whatsapp`, `voice-call`, `mobile-biometric`, `passkey` |
| `validUntil` | datetime | expiry — check against current time before treating a code as usable |
| `requestId` / `operationId` | varchar(255) | nullable |
| `createdAt` / `updatedAt` | datetime | |
| `country` / `source` | varchar | nullable |
| `metadata` | json | nullable |

Find a user's current login OTP by email:

```sql
SELECT m.id, m.userId, u.email, m.code, m.actionType, m.status, m.notificationType, m.validUntil, m.createdAt
FROM multifactor_action_code m
JOIN users u ON u.id = m.userId
WHERE u.email = '<email>' AND m.actionType = 'USER_LOGIN'
ORDER BY m.createdAt DESC
LIMIT 5;
```

By `userId`:

```sql
SELECT id, userId, code, actionType, status, notificationType, validUntil, createdAt
FROM multifactor_action_code
WHERE userId = <userId> AND actionType = 'USER_LOGIN'
ORDER BY createdAt DESC
LIMIT 5;
```

Only trust a row where `status = 'active'` and `validUntil` is still in the
future — `completed`/`expired`/`revoked` rows are stale. A sibling table,
`multifactor_action_admin_code`, exists for admin-initiated codes — same shape,
separate flow.

## `companies`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | int unsigned, PK, auto_increment | |
| `uuid` | char(36) | |
| `name` | varchar(255) | display name — search with `LIKE '%term%'` |
| `status` | enum | `declined`, `in-active`, `active`, `pending`, `deleted`, `onboarding`, `kyb-kyc-verification` |
| `isTest` | tinyint(1) | |
| `createdAt` / `updatedAt` / `deletedAt` | datetime(3) | |

Find a company by name:

```sql
SELECT id, uuid, name, status, isTest, createdAt
FROM companies
WHERE name LIKE '%term%';
```

## `users`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | int unsigned, PK, auto_increment | |
| `uuid` | char(36) | |
| `companyId` | int unsigned | FK to `companies.id` |
| `email` | varchar(255) | |
| `role` | enum | `admin`, `manager`, `employee`, `bookkeeper`, `finance` |
| `status` | enum | same set as `companies.status` |

Adding a user to a company goes through the web dashboard's invite flow
(`POST /web/user/invite-users`, in `modules/v2/web/user/`), which generates
the UUID, sends the onboarding email, and enforces MFA + duplicate-seat
guards — don't hand-insert a row into `users` for a real invite.

## `company_settings`

Per-company feature flags and settings — one row per `(companyId, settingKey)`,
with keys from backend's `COMPANY_SETTINGS_KEYS` enum.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | int unsigned, PK, auto_increment | |
| `companyId` | int unsigned | FK to `companies.id` |
| `settingKey` | varchar(255) | flag name, e.g. `ACCOUNTING_2_QBO`, `AUTO_APPROVE_PAYMENT` |
| `settingValue` | varchar(255) | flags use `on` / `off`; other settings hold numbers or text (`100`, `0.00`, `No`) |
| `settingDescription` | varchar(255) | nullable |
| `createdAt` / `updatedAt` / `deletedAt` | datetime | filter `WHERE deletedAt IS NULL` for live rows |

A key can appear more than once for the same company (seen on dev-20:
`AUTO_APPROVE_PAYMENT` twice for company 6), so use `DISTINCT` or group by
`settingKey` when a single value per key is needed.

Enabled flags for a company:

```sql
SELECT companyId, settingKey, settingValue, updatedAt
FROM company_settings
WHERE companyId = <companyId>
  AND deletedAt IS NULL
  AND settingValue = 'on'
ORDER BY settingKey;
```

## Prod connection note

Prod's backend/monolith database is named **`jeeves`** — it does not follow the dev
`develop_<n>` convention. Confirmed 2026-08-25 via `SELECT DATABASE()` on
`jsql prod`. No 3rd-arg DB override is needed; `prod.env`'s `MYSQL_DB`
already points at it.

Prod `exchange_rates` write cadence is sporadic, not periodic: as of 2026-08-25 the
newest row was `2026-04-29` (a single 112-row bulk run), with prior writes on
2026-03-28, 2026-03-10, 2025-11-25. Do not assume a running cron writes rows
continuously in prod when using row recency as a health signal.
