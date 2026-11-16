---
name: mysql
description: Query Jeeves MySQL dev/preprod/prod databases via the jsql wrapper — env/database selection, which envs accept writes, and secret regeneration. Trigger before any DB access — running a query, fetching a login OTP/MFA code, choosing an env/database, or editing the wrapper/secret files.
---

# Jeeves MySQL — Dev/Prod Database Access

| Env | Target | Database names | Secrets file | Writes |
| --- | --- | --- | --- | --- |
| dev-01…dev-20 | `dev-NN/<service>` | `<service>_NN`; backend `develop_NN` | `$JEEVES_SECRETS_DIR/develop-01.env` … `develop-20.env` | Succeed |
| preprod | `preprod/preprod_<service>` | `preprod_<service>`; backend `preprod` | `$JEEVES_SECRETS_DIR/preprod.env` | Succeed — treat as real shared data |
| development, qa, sandbox | `<env>/<database>` | full database name; list with `SHOW DATABASES` | `$JEEVES_SECRETS_DIR/development.env`, `qa.env`, `sandbox.env` | Succeed — shared |
| prod | `prod/<service>` | `<service>`; backend `jeeves` (full list: "Default" table below) | `$JEEVES_SECRETS_DIR/prod.env` | Read-only: `jsql` runs `SELECT`, `SHOW`, `DESCRIBE`, `EXPLAIN` and `WITH`, and opens the session `READ ONLY` |

On `prod`, `jsql` exits with status 2 for any other statement, before it
connects. On every other env the wrapper sends statements straight to MySQL.

Before any statement that changes data or schema (`INSERT`, `UPDATE`,
`DELETE`, `REPLACE`, DDL), on any env:

1. Get the affected row count: run a `SELECT COUNT(*)` with the statement's
   `WHERE`, or count the rows an `INSERT` adds.
2. Show the user the statement and that count, then wait for the user's yes.
3. Run the statement.

On preprod, name a database that starts with `preprod`. The preprod host also
holds every dev env's databases (`wallet_20`, …) plus stale unprefixed ones
(`accounting`), and the preprod user can read them all — so
`jsql preprod/wallet_20` returns dev-20 data under a preprod header.

## Setup and operations

Credentials, first-time setup, the header colours, environment overrides and
secret regeneration live in `references/setup.md` — read it when a secret
file is missing, the client fails to authenticate, or a tunnel is needed.

## Secret files

Inspect a secret file by its key names only, and keep values out of output
(aws-secrets, "Reporting secrets"):

```bash
cut -d= -f1 "$JEEVES_SECRETS_DIR/develop-05.env"
```

## Running queries

Name the target as `<env>/<service>` in the first argument, so it reads
before the SQL. Env names take the short form: `dev-01` … `dev-20`, `preprod`,
`prod`, plus `development`, `qa` and `sandbox`. On a dev env the wrapper
appends the env number, so `dev-07/accounting` targets `accounting_07`; a
name already ending in a number passes through unchanged. On every other env, write the full database name. Omit the
database to use the env's default from its secrets file.

The command text is logged verbatim, so its shape is what the user reads:

- Wrap the SQL in **single quotes**, and write string values in **double
  quotes** (`"<id>"`) — MySQL reads both quote styles as strings (no
  `ANSI_QUOTES` in `sql_mode`), and single quotes keep the shell out of the
  statement, so backticks and `$` reach MySQL untouched.
- Send one statement per call and leave off the trailing `;` — the output
  then maps to one statement. (The wrapper does run several `;`-separated
  statements; reserve that for a transaction, as `jeeves:provision-wallet-via-sql` does.)
- Keep a short probe on one line:

  ```bash
  jsql dev-07/accounting 'SHOW TABLES'
  ```

- Open anything longer with the quote on the command line, then write the SQL
  flush-left, one clause per line, and close the quote on its own line:

  ```bash
  jsql dev-07/accounting '
  SELECT jeevesVendorId, companyId, isGlCodeMapped,
         isSupplierMapped, isTaxRateMapped,
         trackingCategories, createdAt
  FROM vendor
  WHERE jeevesVendorId = "448f9b5d-b31a-4d98-a789-509fbe74d4a3"
  '
  ```

- When a value itself contains an apostrophe (`"O'Brien"`), feed the SQL
  through a quoted heredoc instead, which holds any character:

  ```bash
  jsql dev-07/billpay <<'SQL'
  SELECT id FROM vendors WHERE companyName = "O'Brien Ltd"
  SQL
  ```

When a task needs several queries, give each its own Bash call and send them
together in one message — they run in parallel, and each shows as its own
command block with its own `<env> · <database>` header and results.

The wrapper passes SQL through unmodified — the server decides what runs, and
each statement succeeds exactly as far as that env's MySQL user permits.
Errors surface on stderr and the wrapper propagates mysql's exit code, so
empty output means an empty result rather than a hidden failure.

## Selecting the service database

Each env hosts one MySQL database **per service**, named `<service>_<envNum>`.
On dev envs, name the service and the wrapper adds the number:

```bash
jsql dev-20/stablecoin 'SELECT ...'
jsql dev-20/wallet 'SELECT ...'
```

**Default:** connect to the database matching the **active service repo**, per
this table (dev and preprod confirmed with `SHOW DATABASES`; prod from the
production DMS config; substitute the env number for `<n>`):

| Service repo | dev-NN | preprod | prod |
| --- | --- | --- | --- |
| wallet-service | `wallet_<n>` | `preprod_wallet` | `wallet` |
| stablecoin-service | `stablecoin_<n>` | `preprod_stablecoin` | confirm with `SHOW DATABASES` |
| accounting-service | `accounting_<n>` | `preprod_accounting` | `accounting` |
| backend / monolith ("jeeves") | `develop_<n>` | `preprod` | `jeeves` |
| billpay-service | `billpay_<n>` | `preprod_billpay` | `billpay` |
| cards-service | `cards_<n>` | `preprod_cards` | `cards` |
| cashback-service | `cashback_<n>` | `preprod_cashback` | `cashback` |
| lumen-engine | `lumen_<n>` | `preprod_lumen` | `lumen` |
| ocr-service | `ocr_<n>` | `preprod_ocr` | `ocr` |
| pricing-engine | `pricing_<n>` | `preprod_pricing` | `pricing` |
| product-account-service | `product_account_<n>` | `preprod_product_account` | `product_account` |
| public-api-service | `publicapi_<n>` | `preprod_publicapi` | confirm with `SHOW DATABASES` |
| risk-service | `risk_<n>` | `preprod_risk` | confirm with `SHOW DATABASES` |
| transactions-service | `transactions_<n>` | `preprod_transactions` | `transactions` |
| underwriting-service | `underwriting_<n>` | `preprod_underwriting` | `underwriting` |
| jeeves-ai | `aiservice_<n>` | `preprod_aiservice` | confirm with `SHOW DATABASES` |
| jumanji | `flows_<n>` | `preprod_flows` | `flows` |
| rfi-agent-service | `rfi_agent_<n>` | `preprod_rfi_agent` | `rfi_agent` |

**Determining the active repo in multi-root workspaces:**

- The session often runs in a workspace with several repos mounted as working
  directories (e.g. `wallet-service` + `public-api-service` + `stablecoin-service`).
- Infer the active service from the files and task currently in play — which
  repo the recent edits and discussion target.
- Prefer that signal over the primary cwd, which is a weaker indicator in a
  multi-root workspace.
- Auto-default only when a single repo is unambiguously in play.

**When ambiguous** (several repos in play and the target unclear, the repo name
maps to no DB, or the user asks generically), ask via `AskUserQuestion`:

1. **Workspace databases first** — one option per repo mounted as a working
   directory, `<service>_<n>`. Put the active repo at the top, marked
   Recommended.
2. **Fill the remaining slots** — the dropdown holds 4 options, so use the
   first 3 for workspace repos and reserve the 4th as an "Other DB" catch-all.
3. **On "Other DB", switch to plain text** — print the remaining service
   databases as a numbered list in a normal chat message and ask for a name or
   number. A text turn has no option limit; a second dropdown would hit the
   same 4-option cap.

Example workspace (`wallet-service` + `public-api-service` + `stablecoin-service`),
active = stablecoin: options → `stablecoin_<n>` (Recommended), `wallet_<n>`,
`publicapi_<n>`, "Other DB".

Discover databases on any env with:

```bash
jsql <env> 'SHOW DATABASES'
```

On preprod this lists every env's databases on the shared host; pick the
`preprod`-prefixed one from the table above.

## Building the query from documented schema

### Common lookups

Check `references/common-lookups.md` first for any lookup request (OTP,
company, user, invites, exchange rate, feature flags, integrations): it maps
each request to its table and schema note. Login OTP lookups run on dev and
preprod only; on prod, decline and say the code reaches the user by email.

### Any other table

Each service database has a schema-notes file at `references/schema/<service>.md`,
named after the dev database prefix — the `<service>` in `jsql dev-NN/<service>`.
One file per service covers its dev, preprod and prod databases.
`references/schema/README.md` holds the one section template. The files so far:

| File | Database |
| --- | --- |
| `references/schema/accounting.md` | `accounting_<n>` |
| `references/schema/billpay.md` | `billpay_<n>` |
| `references/schema/develop.md` | backend `develop_<n>` |
| `references/schema/product_account.md` | `product_account_<n>` |
| `references/schema/stablecoin.md` | `stablecoin_<n>` |
| `references/schema/transactions.md` | `transactions_<n>` (`ut_transactions` columns) |
| `references/schema/wallet.md` | `wallet_<n>` |

Read and write these notes (and `references/common-lookups.md`,
`references/cross-service-links.md`) following `${CLAUDE_PLUGIN_ROOT}/references/write-back.md`.
Before writing a query against a table:

1. Read the schema note first. If it documents the table —
   columns, types, enum values, date/timestamp format, notable FKs — build the
   query straight from that.
2. If the file doesn't exist yet, or the table isn't documented there, discover
   it directly:

   ```bash
   jsql <env>/<service> 'SHOW TABLES'
   jsql <env>/<service> 'DESCRIBE <table>'
   ```

   For enum-like columns, confirm the values actually in use:

   ```bash
   jsql <env>/<service> 'SELECT DISTINCT <col> FROM <table> LIMIT 20'
   ```
3. **Write the schema note in this same turn, before reporting results.** Any
   turn that ran `SHOW TABLES`, `DESCRIBE` or `SELECT DISTINCT` to learn a
   table ends with that table documented in
   `references/schema/<service>.md` (create the file if new). Append a
   section in the shape `references/schema/README.md` gives.

   Document the columns the query used plus any enum values and join keys
   seen; the full `DESCRIBE` output is optional. When the request described
   the task rather than naming the table (e.g. "get the OTP for this user"
   led to `multifactor_action_code`), ask via `AskUserQuestion` whether to add
   it to `references/common-lookups.md`. Show the proposed row in the question
   (request described by the table's subject rather than the user's exact
   wording — name the entity, the likely synonyms and the questions it
   answers, e.g. "Accounting integrations / connections (QBO, Xero, NetSuite)
   — which companies have one, their status"; plus database and table) with options
   **Add to Common lookups** (Recommended) and **Skip**. On Add, write the row
   into `references/common-lookups.md` in this same turn. The schema note itself is written either way.

Each table then only has to be discovered once: later queries read the note
instead of re-running `DESCRIBE`/`SELECT DISTINCT`.

When a task needs data correlated across two service databases (e.g. a
stablecoin deposit and the wallet top-up it produced), check
`references/cross-service-links.md` first — read it before guessing which
columns line up, and append a new section the first time a cross-service query
is worked out.

## Reporting results

Answer with the query's outcome and nothing else. "Connect to dev-07" wants the
connection confirmed, not a database inventory, a syntax reminder and a "what
next?" — the user reads these in a terminal, and every extra line costs context.

- Give the rows, the count, or the one fact asked for.
- Add a caveat only when it changes what the user would do next (an empty
  result that looks like a failure, a value that contradicts the premise).
- Leave out usage examples and restated context.
- When the turn added a schema note, close with one line naming the file and
  table documented.

Present rows as the plugin's `../../references/output-style.md` describes
("Tables for rows, fenced blocks for logs" and its status icons), with ids
full-length and values exactly as MySQL returned them.

**On "raw", return the rows as pretty-printed JSON** in a fenced ```json
block: an array of objects, one per row, keys in the query's column order and
named exactly as returned. Values carry through untouched — full-length ids,
`NULL` as `null`, numbers and dates exactly as MySQL printed them, and no
icons. JSON is the formatting; the data itself stays unedited, with every row
present and none truncated, rounded or reordered.
