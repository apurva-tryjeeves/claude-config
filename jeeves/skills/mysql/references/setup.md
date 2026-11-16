# MySQL setup and operations

Read when a secret file is missing, the client fails to authenticate, or a
tunnel is needed. The env table and the query rules are in `SKILL.md`.

## Credentials

`JEEVES_SECRETS_DIR` defaults to `$HOME/.config/jeeves/mysql` — deliberately
outside any source tree, so credentials stay clear of git, editor indexers and
workspace-wide searches. Set it to relocate them. Keep the directory out of any
git repo; `jsql-pull-secrets` writes a `.gitignore` (`*`) into it as insurance
should it ever land inside one.

Each file holds `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASS`,
`MYSQL_DB`, `MYSQL_SSL`; inspect a file by its key names only, as `SKILL.md`
("Secret files") shows. Each env has its own MySQL user:

| User | Privileges |
| --- | --- |
| `develop_NN` | `ALL` on that env's service databases (`*_NN`) |
| `preprod` | `ALL` on `preprod` and `preprod_*`; `SELECT` on every database on the host, dev ones included |
| prod read replica | read-only |

- Every `develop-NN` file carries a distinct user and password of its own.
- dev-NN and preprod share one host; keep one file per env all the same.
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

## Header and colour

The wrapper prints a `<env> · <database>` header to stderr before the results,
styled by how much a statement can affect there:

| Env | Style | Header note |
| --- | --- | --- |
| `dev-01`…`dev-20`, `development`, `qa`, `sandbox` | green | — |
| `preprod` | yellow | `writes land on shared data` |
| `prod` | inverse red | `read replica` |

The notes print with or without colour. MySQL errors come through in red on
stderr. Colour follows `JEEVES_DB_COLOR=always|never|auto` and defaults to
`always`, so the styling shows in agent session logs as well as a terminal —
set `auto` to limit it to a real terminal, `never` or `NO_COLOR` to switch it
off.

## Environment overrides

Every default matches a standard checkout, so these stay unset in normal use:

| Variable | Default | Applies to |
| --- | --- | --- |
| `JEEVES_SECRETS_DIR` | `$HOME/.config/jeeves/mysql` | both commands |
| `JEEVES_DB_HOST` | the secret file's `MYSQL_HOST`; for the pull, the resolved RDS endpoint | both commands |
| `JEEVES_DB_PORT` | the secret file's `MYSQL_PORT`; `3306` for the pull | both commands |
| `JEEVES_DB_INSTANCE_ID` | `development-db-useast2` | `jsql-pull-secrets` |
| `AWS_PROFILE` | `jeeves_dev` | `jsql-pull-secrets` |
| `MYSQL_CLIENT` | the pinned `mysql-client@8.4` binary | `jsql` |
| `JEEVES_DB_COLOR` | `always` | `jsql` |

`JEEVES_DB_HOST`/`JEEVES_DB_PORT` override the endpoint from the secret file at
query time, so an SSH tunnel or port-forward can be targeted while still using
that env's credentials:

```bash
JEEVES_DB_HOST=127.0.0.1 JEEVES_DB_PORT=13306 jsql dev-13 'SELECT 1'
```

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
`SKIP (secret not found)` and leaves the existing file untouched. Any other
AWS error (an expired SSO session, a denied call) prints the error, stops the
run and exits 1; run `aws sso login --profile jeeves_dev` and pull again. `prod` is
absent from the pull list, per Credentials above.

The DB endpoint is resolved at runtime from the RDS instance id via
`rds:DescribeDBInstances`, so it isn't stored in the repo. Set `JEEVES_DB_HOST`
to the endpoint hostname to skip that lookup — useful when a role lacks the
describe permission:

```bash
JEEVES_DB_HOST=<endpoint-hostname> jsql-pull-secrets
```
