# Common lookups

Requests that go straight to a known table and its ready-made query. Check
this table first for any lookup request; when a request maps to a row, read
the schema note it names and build the query from there.

Read the clone's copy
(`${JEEVES_PLUGIN_SRC:-$HOME/github/apurva-tryjeeves/claude-config}/jeeves/skills/mysql/references/common-lookups.md`)
when it exists — it carries rows not yet released — else this skill's own
copy.

| Request | Database | Table | Reference |
| --- | --- | --- | --- |
| Login OTP / MFA / verification code for a user (dev and preprod only; on prod, decline and say the code reaches the user by email) | `develop_<n>` | `multifactor_action_code` | `references/schema/develop.md` → `multifactor_action_code` |
| Company by name | `develop_<n>` | `companies` | `references/schema/develop.md` → `companies` |
| User by email | `develop_<n>` | `users` | `references/schema/develop.md` → `users` |
| Invites to a company — invited users, pending or accepted | `develop_<n>` | `invite_users` | `references/schema/develop.md` → `invite_users` |
| Exchange rate | `develop_<n>` | `exchange_rates` | `references/schema/develop.md` → `exchange_rates` |
| Feature flags enabled for a company | `develop_<n>` | `company_settings` | `references/schema/develop.md` → `company_settings` |
| Accounting integrations / connections (QBO, Xero, NetSuite via Codat) — which companies have one, their status | `accounting_<n>` | `integration` | `references/schema/accounting.md` → `integration` |

## Adding a row

Add a row in the same turn, after the user approves it, when a request that
named no table had to be searched for (`SKILL.md`, "Any other table" step 3).
Write it into the clone's copy of this file, leave it uncommitted, and tell
the user it is ready to review and push. When the clone is missing, report
the row instead.
