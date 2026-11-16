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
| Prod MySQL | `jsql prod/<database> '<sql>'` |
| Service code | the `jeeves:service-investigator` agent, one per service |

## Start here

- **A single transaction id is the whole question** ("what happened to
  `<uuid>`?") → use the `jeeves:trace-tx` skill instead. It already walks wallet,
  transactions and product-account in order and returns one timeline.
- **Anything broader** — an error signature, a stuck cohort, a bad deploy —
  continue below.

## Read these first

- **Logs** → Skill `jeeves:opensearch` — indices, `@timestamp` / `app_name.keyword` /
  `log` fields, the two trace ids, the `match_phrase` pattern.
- **DB access** → Skill `jeeves:mysql` — the `jsql <env>/<service> '<sql>'` wrapper
  and per-service database selection.
- **Reusable queries** → `../../references/queries.md` — SQL and OpenSearch
  strings the user has shared. Read it when the user refers to a saved query; when the user
  shares a new one, add it to that file following `${CLAUDE_PLUGIN_ROOT}/references/write-back.md`.

## Steps

1. **Ticket.** When a Linear issue is named, read it with
   `get_issue` (`mcp__linear__` or `mcp__claude_ai_Linear__`, whichever is connected) for symptoms, affected entity and time window.
2. **Identifiers.** Extract `traceId` / `jeeves_trace_id`, transaction and
   company ids, provider references.
3. **Prod logs and prod DB.** Delegate steps 3 and 4 to the
   `jeeves:prod-log-investigator` agent (`subagent_type:
   "jeeves:prod-log-investigator"`), passing the ids, the time window and the
   service repo paths; it reads the volume and returns a short finding.
4. **Check the finding.** Read the agent's verdict, evidence table and code
   pointer, and re-run one query yourself only when the evidence contradicts
   the ticket. Query patterns (`term` on a trace id, `match_phrase` on a
   transaction id) are in `jeeves:opensearch` "Query patterns".
5. **Map the code.** From the ticket and the `app_name`s in the logs, identify
   the services involved and fan out the **`jeeves:service-investigator`** agent —
   `subagent_type: "jeeves:service-investigator"`, **one per service, all in a single
   message** so they run in parallel. Give each the repo path
   (`${JEEVES_REPOS_DIR:-$HOME/github/JeevesInc}/<repo>`; when a repo is not
   checked out there, ask the user for its path), the issue and the ids. Synthesize their briefs yourself.
6. **Root-cause timeline.** Request → each service hop → where it diverged,
   carrying ids, statuses and timestamps, and the offending `file:line`.

## Reporting results

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
