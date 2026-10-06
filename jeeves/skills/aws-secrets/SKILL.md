---
name: aws-secrets
description: JeevesInc AWS Secrets Manager paths and SSO authentication — the per-environment, shared and service-name secret conventions. Trigger when locating a service's secret, authenticating to AWS for a Jeeves environment, or reasoning about per-environment AWS config.
---

# Jeeves AWS Secrets

How JeevesInc services authenticate to AWS and where their secrets live. Other
AWS topics get their own skill — `sqs` already does.

## Authentication

| Environments | Account | Region | Profile (role) | Secrets Manager |
|---|---|---|---|---|
| dev-xx, qa, preprod, sandbox | `558433362422` (Jeeves Dev) | `us-east-2` | `jeeves_dev` (Developers) | Yes |
| production | `642613937634` (Jeeves Production) | `us-east-1` | `jeeves_prod_releasemanager` (ReleaseManager) | Yes |
| production | `642613937634` (Jeeves Production) | `us-east-1` | `jeeves_prod` (Developers) | No — OpenSearch only |

All profiles share one SSO session, so one login covers them:

```bash
aws sso login --profile jeeves_dev
```

Confirm a session is live with:

```bash
aws sts get-caller-identity --profile jeeves_dev --region us-east-2
```

## Reporting secrets

List a secret's key names, and extract a single key's value only when the task
needs that value. Show the user key names and paths, never secret values —
when a value has to reach a command, pass it through a variable or a pipe so it
stays out of the transcript.

## Secrets Manager

Path conventions (env-type shapes, the service-name → secret-name mapping, known deviations, and the fetch/list commands) live in `references/secrets-manager.md` — read it before looking up or guessing a secret path. Confirming a new service's pair, a new env-type shape, or a deviation from the standard pattern? Record it in your clone of the plugin (`${JEEVES_PLUGIN_SRC:-$HOME/github/apurva-tryjeeves/claude-config}/jeeves/skills/aws-secrets/references/secrets-manager.md`), leave the change uncommitted and tell the user it is ready to review and push; when that directory is missing, report the finding instead.
