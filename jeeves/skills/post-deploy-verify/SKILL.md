---
name: post-deploy-verify
description: Verify a change after it is deployed to a Jeeves dev or preprod environment — inspect the data it produced, search dev OpenSearch logs for its flow, fix what it got wrong, and extend the tests. Trigger after deploying to dev-xx or preprod, or when testing a just-built change end to end.
---

# Post-Deploy Verification (JeevesInc)

Confirm a freshly deployed change behaves correctly in a real environment, and
fix it where it doesn't.

| Env | DB access | Logs | Writes |
| --- | --- | --- | --- |
| dev-01…dev-20 | `jsql dev-NN/<service> '<sql>'` | `mcp__opensearch-dev__*` | Succeed |
| preprod | `jsql preprod/<database> '<sql>'` | `mcp__opensearch-dev__*` | Succeed — shared data, confirm first |

**Hand-off:** when the user already has an approved test plan to execute and
the `release-test` workflow is installed, it runs the plan and returns a merge
verdict. This skill covers the
looser "I just deployed it, does it work?" pass.

## Read these first

- **Logs** → Skill `opensearch` — indices, `@timestamp` / `app_name.keyword` /
  `log` fields, the two trace ids, the `match_phrase` pattern.
- **DB access** → Skill `mysql` — the `jsql <env>/<service> '<sql>'` wrapper
  and per-service database selection.
- **Reusable queries** → `../../references/queries.md` — read it before
  composing a query, and append a new one there in the same turn the user
  shares one.

## Steps

1. **Ask which environment** the code is deployed to (`dev-xx` or `preprod`),
   and target `dev-NN/<service>` — the wrapper appends the env number.
2. **Mocking plan.** From the services involved, suggest which external
   providers and webhooks to mock — wallet providers (Bridge, Qitech,
   Airwallex, Routefusion, STP, Bexs, Dlocal), accounting (Codat) — and
   confirm the list with the user.
3. **Inspect the data** the flow produced in that env's databases:
   ```bash
   jsql dev-20/wallet '<SELECT ...>'
   ```
   Writing to `preprod` lands on shared data — confirm with the user first.
4. **Search the dev logs** with `mcp__opensearch-dev__*` for the flow's ids and
   errors, using the same `match_phrase` and trace-id patterns as prod.
5. **Fix and verify.** Fix what the run exposed, add or update the test cases
   covering it, and run the suite:
   ```bash
   NODE_ENV=test npx jest <path>
   ```
6. **Commit** following the `git-preferences` skill for message format and the
   co-author trailer. Push when the user asks, then follow that skill's Checks
   poller section for CI.

## Report the verification

Icons, linking and value-rendering vocabulary live in the shared
`../../references/output-style.md` — follow it rather than inventing a format.

- **Verdict line first** — icon, what was verified, and the environment:
  `✅ deposit → wallet top-up verified on dev-20`.
- **Table the checks** — columns `Check | Expected | Actual | Result`, one row
  per thing verified, so a mismatch is visible at a glance.
- **Fence the log lines and rows** that carry the evidence, surrounding output
  left out.

Answer with the verdict and the table, then stop — leave out the queries run
and "want me to test anything else?" follow-ups.
