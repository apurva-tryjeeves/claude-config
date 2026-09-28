---
name: prod-debug
description: Debug a production issue across JeevesInc microservices — trace it through prod OpenSearch logs and prod MySQL, map the code path in each service, and produce a root-cause timeline. Trigger when something in prod is failing, stuck, or producing wrong data and the cause is not yet known.
---

# Production Debugging (JeevesInc)

Find the root cause of a prod issue across Jeeves microservices. Prod is
**read-only**: the server is a read replica and rejects writes on its own.

| Source | Reach it with |
| --- | --- |
| Prod logs | `mcp__opensearch-prod__*` |
| Prod MySQL | `jsql prod/<service_db> "<sql>"` |
| Service code | the `service-investigator` agent, one per service |

## Start here

- **A single transaction id is the whole question** ("what happened to
  `<uuid>`?") → use the `trace-tx` skill instead. It already walks wallet,
  transactions and product-account in order and returns one timeline.
- **Anything broader** — an error signature, a stuck cohort, a bad deploy —
  continue below.

## Read these first

- **Logs** → Skill `opensearch` — indices, `@timestamp` / `app_name.keyword` /
  `log` fields, the two trace ids, the `match_phrase` pattern.
- **DB access** → Skill `mysql` — the `jsql <env>/<database> "<sql>"` wrapper
  and per-service database selection.
- **Reusable queries** → `../../references/queries.md` — SQL and OpenSearch
  strings the user has shared. Read it before composing a query, and append a
  new one there in the same turn the user shares it.

## Steps

1. **Ticket.** Ask for the Linear issue if not given; read it with
   `mcp__linear__get_issue` for symptoms, affected entity and time window.
2. **Identifiers.** Extract `traceId` / `jeeves_trace_id`, transaction and
   company ids, provider references.
3. **Prod logs.** With a trace id, `term`-filter `jeeves_trace_id.keyword` or
   `traceId.keyword` and omit `app_name` — one query returns every service the
   request touched. Otherwise `match_phrase` the id in `log`, scoped by
   `@timestamp` range and `app_name.keyword`. Widen the window when empty, then
   pull the error plus its surrounding breadcrumbs.
4. **Prod DB.** Inspect the state the flow left behind with `SELECT`s:
   ```bash
   jsql prod/wallet "<SELECT ...>"
   ```
5. **Map the code.** From the ticket and the `app_name`s in the logs, identify
   the services involved and fan out the **`service-investigator`** agent —
   `subagent_type: "service-investigator"`, **one per service, all in a single
   message** so they run in parallel. Give each the repo, the issue and the
   ids. Synthesize their briefs yourself.
6. **Root-cause timeline.** Request → each service hop → where it diverged,
   carrying ids, statuses and timestamps, and the offending `file:line`.

## Report the finding

Icons, linking and value-rendering vocabulary live in the shared
`../../references/output-style.md` — follow it rather than inventing a format.

1. **Verdict line first** — icon, where it breaks, the service and `file:line`
   that decides the outcome, the ids.
2. **Per-service map as a table** — columns `Service | Entry point | file:line |
   Role in this flow`, one row per service the fan-out covered.
3. **Log excerpts in fenced blocks** — the handful of lines that carry the
   meaning, surrounding log left out, each prefixed with its local timestamp.
4. **Link every ticket and PR** (`[ACC-1523](…)`, `[#534](…)`) and keep every
   `file:line` exact.

Answer the question asked, then stop — leave out the queries run, index
inventories and "want me to dig further?" follow-ups.
