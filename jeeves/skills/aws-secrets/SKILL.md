---
name: aws-secrets
description: JeevesInc AWS Secrets Manager paths and SSO authentication — the per-environment, shared and service-name secret conventions. Trigger when locating a service's secret, authenticating to AWS for a Jeeves environment, or reasoning about per-environment AWS config.
---

# Jeeves AWS Secrets

How JeevesInc services authenticate to AWS and where their secrets live. Other
AWS topics get their own skill — `sqs` already does.

## Authentication

Dev-xx, qa, and preprod AWS access all live under the `Jeeves Dev - Developers` IAM role, via SSO:

```bash
aws sso login --profile jeeves_dev
```

Confirm a session is live with:

```bash
aws sts get-caller-identity --profile jeeves_dev --region us-east-2
```

## Secrets Manager

Path conventions (env-type shapes, the service-name → secret-name mapping, known deviations, and the fetch/list commands) live in `references/secrets-manager.md` — read it before looking up or guessing a secret path. Confirming a new service's pair, a new env-type shape, or a deviation from the standard pattern? Add it there in the same turn.
