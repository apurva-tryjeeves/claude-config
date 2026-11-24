# Linear Ticket Templates & Multi-Repo Creation

## Reach for a native Linear template first

The workspace carries its own issue templates, and `save_issue` applies one
server-side via `template: "<name or id>"` — filling content, fields and
sub-issues in the shape the team already agreed on. Prefer that over pasting a
markdown shape, so a ticket matches what the team expects.

| Template | Use for | Notes |
| --- | --- | --- |
| `Bug template` | Any bug | The current standard (updated Dec 2025). Ships the org's P0–P3 priority definitions in the body |
| `SPIKE Template` | A timeboxed investigation answering an unknown | Context / Problem / Acceptance Criteria / Additional Details |
| `User Story Template` | PM-driven feature work with a design dependency | Carries Figma, design/release timelines and design+product approvals |
| `Customer Query (Template)` | A question routed in from a customer | |
| `Design Issue - (add the component or page name here)` (id `abae0db6-5238-4171-b455-2f37f20a2ced`) | Design work on a named component or page | Workspace template; teams also carry their own `Design Issue Template`. Put the component/page name in the title |
| `Bug_Template_Cards` | A cards-specific bug | Use over `Bug template` only for cards work |
| `R2 Launch`, `R3 Test-a-Thon` | Launch and test-a-thon events | |

Confirm the list live with `mcp__linear__list_templates` before relying on this
table, and read a template's body with `mcp__linear__get_template` when its
shape matters. Both are workspace-scope, so they reach every team.

`2.0 Customer Bugs and Improvements Form` is a **form** template: applying it
through the API creates the issue with the form unanswered, so fill the fields
in the description instead when a form ticket is wanted.

A `description` passed alongside `template` replaces the template body outright
rather than merging — omit `description` to keep the template's own body, then
edit the created issue with `patch` to fill the placeholders.

### Applying the bug template

```text
save_issue(team: "Product - Wallet", title: "<bug title>", template: "Bug template")
```

Add on top of what the template asks for: **lead with the reporter's own
words** — quote rather than paraphrase, since their phrasing usually carries
detail a summary loses. The template body also ends with a P0–P3 reference
table carrying its own instruction to delete it once the priority is chosen;
follow that, so the shipped ticket keeps only the priority that applies.

Once a native template's body is on the issue, restyle its section headers
with the `## <emoji> Header` convention from `${CLAUDE_PLUGIN_ROOT}/references/output-style.md`
using `patch`, keeping the template's wording.

## Shapes for the types Linear has no template for

Section headers and order follow ${CLAUDE_PLUGIN_ROOT}/references/doc-spine.md.

Use these when no native template fits. Linear's own guidance is to write only
as much as the task needs rather than fill out a form
([Write issues not user stories](https://linear.app/method/write-issues-not-user-stories),
[Creating issues](https://linear.app/docs/creating-issues)) — description is
optional, and only title + status are required. Drop any section that adds
nothing for the ticket at hand.

### Task / sub-ticket

The everyday engineering ticket: one change in one repo, often a sub-ticket of a
parent. Write the Solution when the approach is decided; leave it out when the
assignee chooses it.

```markdown
## ❗ Problem
- **<Lead>:** <what is missing or broken today>

## 🛠️ Solution
- **<Decision>:** <behaviour it gives>, in `<service>` `<key/path>`.

## ✅ Acceptance criteria
- [ ] **<Check>:** <observable result a reviewer can verify>

## 🔗 References
- **Parent:** <PARENT-ID>
- **Design doc:** <Notion link>
```

### Feature / initiative (engineering-initiated)

`User Story Template` suits PM-driven work with a design dependency. For
backend or platform work started by engineering, this leaner shape fits better.
Write the Problem section as bullets — one per distinct fact or cause — so a
problem with several symptoms stays scannable.

```markdown
## ❗ Problem
- **<Lead>:** <fact or cause — what's missing or broken>
- **<Lead>:** <why it matters — what it causes>

## 🎯 Goal
<what success looks like, in one or two sentences>

## 📐 Scope
- **<Area>:** <in-scope item>

**Out (this phase):** <excluded item, only when the edge is ambiguous>

## ✅ Acceptance criteria
- [ ] **<Check>:** <observable result a reviewer can verify>

## ❓ Open questions
1. <question> — owner: <name>

## 🔗 References
- **Design doc:** <Notion link>
```

A parent ticket's sub-tickets live in Linear's Sub-issues section; the description holds context and done-when.

### Post-mortem / incident

File this once the incident is resolved, so the write-up sits with the fix
rather than in chat. Link the hotfix PR and the tickets that carried the
interim and permanent fixes.

```markdown
## 📰 What happened
<one paragraph a reader outside the team can follow>

## 💥 Impact
* **Blast radius:** <orgs/accounts/currencies/services affected>
* **Duration:** <first bad event → resolved, with timestamps>
* **Detected by:** <alert name, a customer report, or a person noticing>

## 🕒 Timeline
| Time | Event |
| --- | --- |
| <HH:MM TZ> | <what happened or what was done> |

## 🔍 Root cause
<the actual mechanism, with `file:line` or the query/config that caused it>

## 🛠️ Resolution
* **Interim fix:** <what stopped the bleeding> — <PR link>
* **Permanent fix:** <what keeps it fixed> — <PR link>

## 🕳️ What let it through
* <the gap — missing alert, untested path, silent failure mode>

## 📌 Follow-ups
- [ ] <action> — <owner>, filed as <ticket link>
```

Detection deserves its own honest line: an incident a customer reported before
any alert fired is a monitoring gap, and that belongs in Follow-ups.

### Planning / breakdown

For turning a known body of work into tasks. A SPIKE answers an open question;
this plans work already understood.

```markdown
## 🎯 Goal
<what exists at the end that doesn't today>

## 🛠️ Solution
<the chosen shape, in a few sentences — and the option rejected, when the
choice is one a reviewer would otherwise ask about>

## 🧩 Work breakdown
| # | Task | Repo | Depends on |
| --- | --- | --- | --- |
| 1 | <task> | <repo> | — |

## ⚠️ Risks
* <what could make this take longer or land badly>

## 🚫 Out of scope
* <explicitly excluded>
```

Create the per-task tickets from the breakdown table once agreed, following
the multi-repo flow below, and keep this ticket as the parent.

### Tech debt / cleanup

Lead with the cost of leaving it alone — that is what earns the ticket a slot
in a cycle.

```markdown
## 📍 Current state
<what the code does now, with `file:line` for the worst offenders>

## 💸 Cost of leaving it
* <what it slows down, breaks, or hides today>

## 🎯 Goal
<what it looks like once done>

## 📐 Scope
* <file/module in scope>

**Behaviour change:** none — <or name exactly what changes>

## ✅ Acceptance criteria
- [ ] **<Check>:** <how a reviewer confirms nothing regressed: tests, a dev-NN run, a log check>
```

The **Behaviour change** line matters most on a refactor: a reviewer's first
question is whether this is meant to be a no-op.

### Monitoring & alerting

```markdown
## 🙈 What goes unnoticed today
<the failure that currently reaches production without anyone being paged>

## 📡 Signal
* **Source:** <OpenSearch index / metric / log line>
* **Query:** <the exact query or filter>
* **Condition:** <threshold and window that should fire>

## 📣 Destination
* **Channel:** <Slack channel>
* **Message:** <what the alert says, so it's actionable at 3am>

## 🎚️ Tuning
<expected volume, and what makes this noisy enough to be ignored>
```

Name the exact query — an alerting ticket whose signal is left as "add
monitoring" gets rediscovered from scratch when someone picks it up.

## Creating tickets from a multi-repo plan (Notion PRD work)

When a plan built from a Notion PRD spans more than one repo, create one
ticket per repo/task rather than a single umbrella ticket — each repo's work
gets its own title, description, team, and reviewer, so it tracks and closes
independently.

1. Create each per-repo ticket first with `save_issue`, collecting their
   issue identifiers as they're created.
2. Cross-link the sibling pairs that have no `blocks`/`blockedBy` link: call
   `save_issue` again on each ticket, passing `relatedTo` with the identifiers
   of those siblings. Linear keeps one relation per pair, so `relatedTo` on a
   blocking pair replaces the blocking relation; for such a pair, skip
   `relatedTo` or re-apply `blockedBy` afterwards (last write wins). Then read
   the relations back with `get_issue(id, fields: ["id", "relations"])` and
   confirm every `blocks`/`blockedBy`/`relatedTo` link is present. A sibling id
   written bare in a description links only when that ticket already exists at
   save time; re-save the line (a `patch` touching it) to link an id for a
   ticket created later.
3. If the PRD names one ticket as the parent/tracking issue (see the `WAL-5674`
   pattern — a parent ticket with the requirements and rollout plan, with
   build work filed as sub-tasks once scoped), use `parentId` for that
   ticket's children instead of `relatedTo` — parent/child expresses "this
   tracks that work," while `relatedTo` expresses "these are peers, done
   together."
4. Title each per-repo ticket `[<repo-name>] <title>` and leave the
   multi-repo parent unprefixed (`SKILL.md` → "Title").

Show each ticket's whole draft (the `SKILL.md` "Create or update an issue"
rule) and wait for the user's yes before creating any of them.
