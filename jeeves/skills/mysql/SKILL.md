---
name: mysql
description: Query Jeeves MySQL dev/preprod/prod databases via the jsql wrapper — env/database selection, which envs accept writes, and secret regeneration. Trigger before any DB access — running a query, fetching a login OTP/MFA code, choosing an env/database, or editing the wrapper/secret files.
---

# Jeeves MySQL — Dev/Prod Database Access

| Env | Target | Secrets file | Writes |
| --- | --- | --- | --- |
| dev-01…dev-20 | `dev-NN/<service>` | `$JEEVES_SECRETS_DIR/develop-01.env` … `develop-20.env` | Succeed |
| preprod | `preprod/<database>` | `$JEEVES_SECRETS_DIR/preprod.env` | Succeed — treat as real shared data |
| prod | `prod/<database>` | `$JEEVES_SECRETS_DIR/prod.env` | Rejected by the server (read replica, `ERROR 1290`) |

The wrapper sends statements straight to MySQL, so **the server is the only
thing that stops a write**. Read intent from the table above before running
anything that modifies data, and confirm with the user before writing to
`preprod`.

## Credentials

`JEEVES_SECRETS_DIR` defaults to `$HOME/.config/jeeves/mysql` — deliberately
outside any source tree, so credentials stay clear of git, editor indexers and
workspace-wide searches. Set it to relocate them. Keep the directory out of any
git repo, and keep its `.gitignore` (`*`) as insurance should it ever land
inside one.

Each file holds `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASS`,
`MYSQL_DB`, `MYSQL_SSL`, scoped per environment:

- Each env has its **own MySQL user**, scoped to a single database.
- Every `develop-NN` file carries a distinct user and password of its own.
- Keep one file per env, even where several share a host.
- A database override changes only the database — the user and password still
  come from the env's file.

`prod.env` is maintained by hand: its secret sits outside the accessible
Secrets Manager account, so the pull skips it. Create it with the same six
fields from the prod read-replica credentials stored in Keeper, `chmod 600`.

## First-time setup

1. Install a MySQL **8.4** client. The servers authenticate with
   `mysql_native_password`, which the 9.x client dropped as a built-in:

   ```bash
   brew install mysql-client@8.4
   ```

   The wrapper prefers the pinned 8.4 keg, then falls back to `mysql` on
   `PATH`. Point `MYSQL_CLIENT` at a specific binary to override the search.

2. Authenticate to AWS, then pull the credentials:

   ```bash
   aws sso login --profile jeeves_dev
   jsql-pull-secrets
   ```

3. Confirm access:

   ```bash
   jsql dev-13 'SELECT 1'
   ```

`jsql` ships in this plugin's `bin/`, which Claude Code puts on the Bash
tool's `PATH` while the plugin is enabled — so the bare command resolves with
no setup.

## Running queries

Name the target as `<env>/<service>` in the first argument, so it reads
before the SQL. Env names take the short form: `dev-01` … `dev-20`, `preprod`,
`prod`. On a dev env the wrapper appends the env number, so `dev-07/accounting`
targets `accounting_07`; a name already ending in a number passes through
unchanged. On preprod and prod, write the full database name. Omit the
database to use the env's default from its secrets file.

The command text is logged verbatim, so its shape is what the user reads:

- Wrap the SQL in **single quotes**, and write string values in **double
  quotes** (`"<id>"`) — MySQL reads both quote styles as strings (no
  `ANSI_QUOTES` in `sql_mode`), and single quotes keep the shell out of the
  statement, so backticks and `$` reach MySQL untouched.
- Leave off the trailing `;` — the wrapper sends one statement per call.
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

A trailing 3rd argument also sets the database and takes precedence over the
slash form; the slash form is preferred for new commands.

### Header and colour

The wrapper prints a `<env> · <database>` header to stderr before the results,
styled by how much a statement can affect there:

| Env | Style | Header note |
| --- | --- | --- |
| `dev-01`…`dev-20` | green | — |
| `preprod` | yellow | `writes land on shared data` |
| `prod` | inverse red | `read replica` |

The notes print with or without colour. MySQL errors come through in red on
stderr. Colour follows `JEEVES_DB_COLOR=always|never|auto` and defaults to
`always`, so the styling shows in agent session logs as well as a terminal —
set `auto` to limit it to a real terminal, `never` or `NO_COLOR` to switch it
off.

### Environment overrides

Every default matches a standard checkout, so these stay unset in normal use:

| Variable | Default | Applies to |
| --- | --- | --- |
| `JEEVES_SECRETS_DIR` | `$HOME/.config/jeeves/mysql` | both commands |
| `JEEVES_DB_HOST` | the secret file's `MYSQL_HOST`; for the pull, the resolved RDS endpoint | both commands |
| `JEEVES_DB_PORT` | the secret file's `MYSQL_PORT`; `3306` for the pull | both commands |
| `JEEVES_DB_INSTANCE_ID` | `development-db-useast2` | `jsql-pull-secrets` |
| `MYSQL_CLIENT` | the pinned `mysql-client@8.4` binary | `jsql` |
| `JEEVES_DB_COLOR` | `always` | `jsql` |

`JEEVES_DB_HOST`/`JEEVES_DB_PORT` override the endpoint from the secret file at
query time, so an SSH tunnel or port-forward can be targeted while still using
that env's credentials:

```bash
JEEVES_DB_HOST=127.0.0.1 JEEVES_DB_PORT=13306 jsql dev-13 'SELECT 1'
```

## Selecting the service database

Each env hosts one MySQL database **per service**, named `<service>_<envNum>`.
On dev envs, name the service and the wrapper adds the number:

```bash
jsql dev-20/stablecoin 'SELECT ...'
jsql dev-20/wallet 'SELECT ...'
```

**Default:** connect to the database matching the **active service repo**, per
this table (confirmed on dev-20; substitute the env number for `<n>`):

| Service repo | Database |
| --- | --- |
| wallet-service | `wallet_<n>` |
| stablecoin-service | `stablecoin_<n>` |
| accounting-service | `accounting_<n>` |
| backend / monolith ("jeeves") | `develop_<n>` |
| billpay-service | `billpay_<n>` |
| cards-service | `cards_<n>` |
| cashback-service | `cashback_<n>` |
| lumen-engine | `lumen_<n>` |
| ocr-service | `ocr_<n>` |
| pricing-engine | `pricing_<n>` |
| product-account-service | `product_account_<n>` |
| public-api-service | `publicapi_<n>` |
| risk-service | `risk_<n>` |
| transactions-service | `transactions_<n>` |
| underwriting-service | `underwriting_<n>` |
| jeeves-ai | `aiservice_<n>` |
| jumanji | `flows_<n>` |
| TBD | `rfi_agent_<n>` |

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

preprod/prod schema names may differ from the `_<n>` dev convention — confirm
there.

## Building the query from documented schema

### Common lookups

For these requests, go straight to the listed table and its ready-made query:

| Request | Database | Table | Reference |
| --- | --- | --- | --- |
| Login OTP / MFA / verification code for a user | `develop_<n>` | `multifactor_action_code` | `references/schema/backend.md` → `multifactor_action_code` |
| Company by name | `develop_<n>` | `companies` | `references/schema/backend.md` → `companies` |
| User by email | `develop_<n>` | `users` | `references/schema/backend.md` → `users` |
| Exchange rate | `develop_<n>` | `exchange_rates` | `references/schema/backend.md` → `exchange_rates` |
| Feature flags enabled for a company | `develop_<n>` | `company_settings` | `references/schema/backend.md` → `company_settings` |
| Accounting integrations / connections (QBO, Xero, NetSuite via Codat) — which companies have one, their status | `accounting_<n>` | `integration` | `references/schema/accounting.md` → `integration` |

A row is added when a request that didn't name its table had to be searched for
and the user approves the row (see step 3 below).

### Any other table

Each service database has a schema-notes file at `references/schema/<service>.md`
(service name matches the table above, e.g. `wallet.md`, `stablecoin.md` — one
file per service, shared across its `_<n>` env variants). Before writing a query
against a table:

1. Read `references/schema/<service>.md` first. If it documents the table —
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
   table ends with that table documented in `references/schema/<service>.md`
   (create the file if new). Resolve the path from this skill's base
   directory. Append a section in this shape:

   ````markdown
   ## `<table>`

   <one line: what the table holds and which request it answers>

   | Column | Type | Notes |
   | --- | --- | --- |
   | `<col>` | <type> | <enum values, FK target, date format> |

   <the working query, fenced as sql>
   ````

   Document the columns the query used plus any enum values and join keys
   seen; the full `DESCRIBE` output is optional. When the request described
   the task rather than naming the table (e.g. "get the OTP for this user"
   led to `multifactor_action_code`), ask via `AskUserQuestion` whether to add
   it to **Common lookups** above. Show the proposed row in the question
   (request described by the table's subject rather than the user's exact
   wording — name the entity, the likely synonyms and the questions it
   answers, e.g. "Accounting integrations / connections (QBO, Xero, NetSuite)
   — which companies have one, their status"; plus database and table) with options
   **Add to Common lookups** (Recommended) and **Skip**. On Add, write the row
   in this same turn. The schema note itself is written either way.

Each table then only has to be discovered once: later queries read the note
instead of re-running `DESCRIBE`/`SELECT DISTINCT`.

When a task needs data correlated across two service databases (e.g. a
stablecoin deposit and the wallet top-up it produced), check
`references/cross-service-links.md` first the same way — read it before
guessing which columns line up, and append a new section there the first time a
cross-service query is worked out.

## Regenerating secret files

`jsql-pull-secrets` re-pulls credentials from AWS Secrets Manager (dev
host, profile `jeeves_dev`) and writes them into the secrets directory:

```bash
jsql-pull-secrets                # pull all envs
jsql-pull-secrets develop-05     # pull one env
```

The single-env argument is the **full** env name (`develop-05`, `preprod`),
since it maps straight onto the Secrets Manager id — distinct from the short
alias (`dev-05`) that `jsql` takes. A name with no matching secret reports
`SKIP (secret not found)` and leaves the existing file untouched. `prod` is
absent from the pull list, per Credentials above.

The DB endpoint is resolved at runtime from the RDS instance id via
`rds:DescribeDBInstances`, so it isn't stored in the repo. Set `JEEVES_DB_HOST`
to the endpoint hostname to skip that lookup — useful when a role lacks the
describe permission:

```bash
JEEVES_DB_HOST=<endpoint-hostname> jsql-pull-secrets
```

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

**Present rows as a markdown table.** One column per selected column, one row
per record, headers matching the column names the query returned. This is the
default for every result set, including a single row.

In that table view, a status column (`status`, `accountStatus`, `kycStatus`,
`result`) reads faster with its icon beside the value it already holds — e.g.
`✅ ACTIVE`, `⏳ PENDING`, `❌ FAILED`. The plugin's
`../../references/output-style.md` carries the shared icon set, so a status renders
the same here as in the Jenkins, Linear and OpenSearch skills. Ids stay
full-length, and the underlying value stays exactly as MySQL returned it — the
icon sits alongside it rather than replacing it.

**On "raw", return the rows as pretty-printed JSON** in a fenced ```json
block: an array of objects, one per row, keys in the query's column order and
named exactly as returned. Values carry through untouched — full-length ids,
`NULL` as `null`, numbers and dates exactly as MySQL printed them, and no
icons. JSON is the formatting; the data itself stays unedited, with every row
present and none truncated, rounded or reordered.

Run the query on its own — the command text is logged verbatim, so `echo`
banners, section separators and label lines around it double what the user
reads. The wrapper's `<env> · <database>` header already names the target. Run
one query per call, sending several calls together in one message, rather
than chaining queries behind separators.
