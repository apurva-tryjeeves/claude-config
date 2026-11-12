# Confirmed envs

One row per env where `invite-dev-company-user` has run end to end with the
shared `jeeves-cms-dev` login. For an env with no row yet, run the flow, then
add its row in the same turn. When an env needs a login of its own, store it as
the Keychain item `jeeves-cms-<env>` and name that item in the row.

| Env | Keychain item | Last confirmed | Proof |
| --- | --- | --- | --- |
| `develop-16` | `jeeves-cms-dev` | 12 Nov 2026 | invite 22 → user 12, company 11 |

## Mail delivery per env

One row per env: the `ALLOWED_EMAIL_DOMAINS` value notification-service runs
with, on top of the built-in `@tryjeeves.com`. Read it fresh in step 2, and
update the row in the same turn the value or a delivery result changes.

| Env | `ALLOWED_EMAIL_DOMAINS` | Set in | Confirmed |
| --- | --- | --- | --- |
| `develop-16` | `@conexa.ai` | `/develop-16/notification-service/notification-secrets` | 12 Nov 2026 · invite 44 to `rodrigo@conexa.ai` sent (SES 200) |
