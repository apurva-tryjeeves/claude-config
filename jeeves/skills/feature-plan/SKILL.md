---
name: feature-plan
description: Plan a new feature across JeevesInc microservices from a Notion spec or Linear ticket — confirm the services in scope, map their current code in parallel, and write a per-service implementation plan. Trigger when scoping or designing work that has not been written yet.
---

# Feature Planning (JeevesInc)

Turn a spec into a per-service implementation plan, grounded in what the code
and data look like today. Work against a **dev-xx** environment — ask which.

**Hand-off:** once the plan is approved and the work needs Linear tickets, hand
it to the `prd-split` workflow (one ticket per repo) and then `prd-implement`
when those workflows are installed; otherwise hand the plan back to the user.
This skill produces the plan those read from.

## Read these first

- **DB access** → Skill `jeeves:mysql` — the `jsql <env>/<service> '<sql>'` wrapper
  and per-service database selection.
- **Reusable queries** → `../../references/queries.md` — read it before
  composing a query; when the user shares a new one, add it to that file following
  `${CLAUDE_PLUGIN_ROOT}/references/write-back.md`.
- **GitHub** → `mcp__github__*`, or `gh` via Bash.

## Steps

1. **Find the spec.** Search Linear and Notion; ask the user for the Notion
   spec and Linear ticket links when neither is given, then read them.
2. **Scope the services.** Propose the microservices involved from the spec,
   then **ask the user to confirm** which are in scope before mapping anything.
3. **Map the current state.** Fan out the **`jeeves:service-investigator`** agent —
   `subagent_type: "jeeves:service-investigator"`, **one per confirmed service, all in
   a single message** so they run in parallel. Give each the repo, the feature
   and any identifiers in play. Synthesize their maps yourself.
4. **Data shape.** Connect to a **dev-xx** database (ask which env) and inspect
   the rows and key patterns the feature has to fit:
   ```bash
   jsql dev-20/wallet '<SELECT ...>'
   ```
5. **Write the plan.** One section per microservice — changes, new or changed
   APIs, DB migrations, config, inter-service contracts, risks — plus a
   sequencing section saying what lands first. Save it as a reviewable markdown
   file.

## Report the plan

Icons, linking and value-rendering vocabulary live in the shared
`../../references/output-style.md` — follow it rather than inventing a format.

- **Lead with the service list** as a table — columns `Service | Change |
  Depends on` — so the sequencing reads before the detail.
- **Keep every `file:line` exact**, so the reader jumps straight to the code
  the plan changes.
- **Link the spec and the ticket** rather than restating them.

Point the user at the saved plan file, then stop — leave out a recap of its
sections and "shall I start implementing?" follow-ups.
