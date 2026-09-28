# Secrets Manager — path conventions

Grows with use: whenever a lookup confirms a new service's `service-dir`/`secret-leaf` pair, a new environment-type shape, or a deviation from the standard pattern, add it here in the same turn.

Every secret path has the shape `/{env}/{service-dir}/{secret-leaf}`. `service-dir` and `secret-leaf` are fixed per service and identical across every environment type — only `{env}` changes. Confirmed by listing all ~1484 secrets (`aws secretsmanager list-secrets`) and diffing the `/shared/`, `/develop-20/`, `/preprod/`, and `/qa/` prefixes: the same 40 `service-dir/secret-leaf` pairs appear under each.

## Environment-type convention

| Env type | Path template | Example |
| --- | --- | --- |
| Per-dev-env (`develop-01`…`develop-20`, `dev-jaidev-*`, `sld-*`, `drill`, `sandbox`) | `/{env}/{service-dir}/{secret-leaf}` | `/develop-20/wallet-service/wallet-secrets` |
| Shared across all dev-xx envs | `/shared/{service-dir}/{secret-leaf}` | `/shared/wallet-service/wallet-secrets` |
| qa | `/qa/{service-dir}/{secret-leaf}` | `/qa/wallet-service/wallet-secrets` |
| preprod | `/preprod/{service-dir}/{secret-leaf}` (one combined file, no separate shared) | `/preprod/wallet-service/wallet-secrets` |
| Local-dev bootstrap (separate convention — see below) | `/build/{service-dir}/{leaf}`, leaf varies (`env-local`, `env-template`, `env-example`, `env-qa`, ...) | `/build/wallet-service/env-local` |

For a dev-xx environment, look up a value by checking **both** the env-specific and shared secrets for that service — env-specific holds per-environment overrides (e.g. a dev-20-only DB host), shared holds values common to every dev-xx environment for that service (e.g. sandbox API credentials). A key can live in either, so check both. preprod and qa each carry their own complete, standalone secret file, independent of `/shared/`.

**Separate convention — local-dev bootstrap file.** `/build/{service-dir}/...` is a different thing: a full flat `.env`-format snapshot that a service's own `make get_env_file`-style target pulls down to seed a fresh local checkout. Its leaf name varies per service (`env-local`, `env-template`, `env-example`, `env-qa`, `env-drill`, `env-dev-aws-tryjeeves`, `env-preprod-tryjeeves` all appear). Treat it as a partial snapshot: it can omit keys that the env/shared secrets carry. Check the env/shared secrets directly when a key is missing from the bootstrap file.

## Service-name → secret-name convention

`service-dir` is the service's canonical repo-ish name; `secret-leaf` is a per-service short alias assigned independently of the service name — look it up here (e.g. `payment-transfer` → `pts-secrets`, `expense-management` → `expm-secrets`, `trunarrative` → `tn-secrets`).

| service-dir | secret-leaf |
| --- | --- |
| accounting-service | accounting-secrets |
| ai-service | ai-secrets |
| ai-web | aiweb-secrets |
| ap-data-connector | connector-secrets |
| api-backend | api-be-secrets |
| auth-service | auth-secrets |
| banking-service | banking-secrets |
| billpay-service | billpay-secrets |
| btg-integration | btg-secrets |
| cards-gateway | gateway-secrets |
| cards-service | cards-secrets |
| cashback-service | cashback-secrets |
| company-service | company-secrets |
| credit-service | credit-service-secrets |
| credit-statements | credit-secrets |
| drive-service | drive-secrets |
| expense-management | expm-secrets |
| flows-service | flows-secrets |
| health-check-service | healthcheck-secrets |
| jai-dev-agent | jai-dev-agent-secrets |
| jeeves-mcp-server | jeeves-mcp-secrets |
| loan-worker | loan-secrets |
| lumen-engine | lumen-secrets |
| merchant-cleaner | merchant-cleaner-secrets |
| notification-service | notification-secrets |
| ocr-service | ocr-secrets |
| openbanking-service | openbanking-secrets |
| payment-transfer | pts-secrets |
| pricing-engine | pricing-secrets |
| product-account | product-account-secrets |
| public-api-service | public-api-secrets |
| reconciliation-service | reconciliation-secrets |
| rfi-agent | rfi-agent-secrets |
| risk-service | risk-secrets |
| simulation-service | simulation-secrets |
| stablecoin-service | stablecoin-service-secrets |
| transactions-service | transactions-secrets |
| trunarrative | tn-secrets |
| underwriting-service | underwriting-secrets |
| utv-worker | utvworker-secrets |
| wallet-service | wallet-secrets |

A few services use a different shape than the plain `{env}/{service-dir}/{secret-leaf}` pattern — check these directly:
- `{env}/dbt-accounting/env-config` (not `-secrets`)
- `{env}/spei-bulk-transfer/pts-secrets-batch` (preprod/qa only, not seen under `/shared/`)
- `qa/simulation-server/simulationserver-secrets` (distinct from `simulation-service/simulation-secrets`)
- `preprod/universal-transactions/glue-mysql-db-credentials`

## Commands

Fetch a secret:

```bash
aws --profile jeeves_dev --region us-east-2 secretsmanager get-secret-value \
  --secret-id /shared/wallet-service/wallet-secrets --query SecretString --output text
```

The value is one line of JSON (not `KEY=VALUE` pairs) — pipe through `jq` or `python3 -c "import json,sys; ..."` to inspect or extract individual keys.

List every secret (paginates automatically, ~1484 total as of last check):

```bash
aws --profile jeeves_dev --region us-east-2 secretsmanager list-secrets --query "SecretList[].Name" --output json
```
