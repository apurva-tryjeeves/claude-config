---
name: linear
description: Look up, create, update and query JeevesInc Linear issues, and draft replies for engineering, product or support audiences. Trigger on a Linear ticket id (e.g. WAL-1234) or URL, starting work on a ticket, creating or updating an issue, open-ticket or cycle questions, or drafting a reply; load before `save_issue` or `save_comment`. `@jaidev` comments go to the jaidev skill.
---

# Linear

Workspace: `jeeves` (https://linear.app/jeeves). The Linear tools come from
whichever Linear server is connected — `mcp__linear__*` (the project's Linear
MCP) or `mcp__claude_ai_Linear__*` (the claude.ai connector); both take the
same parameters. Tool names below use the `mcp__linear__` form; call the
connected one. Always confirm an issue's current state and content with these
tools before acting on it.

## Common teams

| Team | Prefix | Used for |
|---|---|---|
| Product - Wallet | `WAL` | wallet-service, sequelize-db-models, jeeves-simulation-server |
| EPD - Accounting ERP | `ACC` | accounting-service, jeeves-ai (GL code work) |

Other teams exist in the workspace (Devops, Product - Cards, Design, QA
Automation, JeevesAI, etc.) — pass the team name or prefix straight through
to the tools when a ticket or request names one of those instead.

## Workflow states

The two teams run the same states, with one difference: `EPD - Accounting ERP`
adds `Triage` as the landing state for incoming work, which `Product - Wallet`
has no equivalent of.

`Backlog` → `Triage` (ACC only) → `Design To Do` / `To Do` / `Dev Ready` →
`Design In Progress` / `In Progress` → `In Review` → `QA` →
`Production Ready` → `Done`

`Canceled` and `Duplicate` are terminal exits from any state.

Every state also carries a `type`, which is what the API filters on and what
picks the reporting icon. A state's type follows its position in the pipeline
rather than its name, so `Production Ready` already counts as completed and
`Design In Progress` still counts as unstarted:

| Type | States | Icon |
| --- | --- | --- |
| `backlog` | Backlog | ⚪ |
| `triage` | Triage (ACC only) | ⚪ |
| `unstarted` | Design To Do, To Do, Dev Ready, Design In Progress | ⚪ |
| `started` | In Progress, In Review, QA | ⏳ |
| `completed` | Production Ready, Done | ✅ |
| `canceled` | Canceled | ⛔ |
| `duplicate` | Duplicate | ⛔ |

Filter by type when the request is about progress ("what's in flight" →
`started`, "what's finished" → `completed`), and by exact state name when the
user names one. Confirm a team's live states with
`mcp__linear__list_issue_statuses` before relying on this table for a team
outside the two above.

## Ways of working

### Start work on a ticket

When the user starts work on a ticket (picks it up, branches for it, or asks
to implement it), update it in the same turn, before branching or writing
code — even when the task brief doesn't mention Linear:

1. Fetch the ticket with `mcp__linear__get_issue`.
2. Set `state: "In Progress"`, put it in the team's current cycle (resolve it
   live with `list_cycles`), and assign it to the user. Delegating the ticket
   to Jaidev leaves it unassigned to the user; that flow follows the
   `jaidev` skill.
3. For a missing **estimate** or **project**, fetch live options, narrow them
   as described in "Team, project, estimate, cycle" below, and ask with one
   `AskUserQuestion` call.
4. Show the field changes as one list — state, cycle, assignee, and any
   estimate or project — and wait for the user's yes. Then save them in one
   `mcp__linear__save_issue` call and continue with the work.

### Finish work on a ticket

Once the work is pushed or finished:

1. Draft any missing estimate or cycle, the commit or PR link, and an
   outcome comment: done and open items, verification results, and blockers
   with their ticket ids.
2. Confirm the draft with one `AskUserQuestion`, then save it. Then move the
   state as its own confirmed step: `Done` when every ticket item is complete,
   `In Review` when review is next, `In Progress` while an item is open.
3. List candidate related tickets as suggestions, and add a `relatedTo` link
   only for the ones the user approves.
4. Treat any change to the ticket between your saves as the user's deliberate
   edit, and keep it — re-read the ticket when a field looks lost.

## Look up a ticket

Given an ID (`WAL-1234`) or a Linear URL, fetch it with `mcp__linear__get_issue`:
- Pass `includeRelations: true` when the user needs blocking/related/duplicate context.
- Pass `includeReleases: true` when they ask which release it shipped in.
- Follow up with `mcp__linear__list_comments` for comment history (e.g. to ground a reply).

## Create or update an issue

Use `mcp__linear__save_issue`:
- Creating: pass `title` and `team` (name or prefix) at minimum; add `description`,
  `assignee`, `labels`, `priority`, `project`, `estimate`, `cycle` as given or
  resolved below.
- Updating: pass `id` and only the fields changing. Use `patch` instead of
  `description` when editing part of a long description rather than replacing
  it whole.

Show the whole draft and wait for the user's explicit yes before calling
`save_issue`, even when the request that asked for the ticket already says
"create":

- the fields: title, team, parent, project, milestone, assignee, priority,
  estimate and relations;
- the description as raw markdown in a ` ````markdown ` fence, so headings,
  checkboxes and code blocks show exactly as they will post;
- for an update, the fields changing and the `patch` text or new description.

The user's reply to the shown draft ("yes", "create it", "post it") is the
approval.

### Move a ticket to another state

Pass `id` plus `state` (the state's name, e.g. `In Review`, or its type). When
the user names a direction rather than a state — "move it forward", "it's
done" — confirm which state they mean against the pipeline above, since most
positions have several plausible next states.

### Fields that replace vs. append

Several `save_issue` fields overwrite the whole set, so reach for the
incremental form when adding to what a ticket already has:

| Intent | Field | Behaviour |
| --- | --- | --- |
| Add a label, keep the rest | `addLabels` | Append-only |
| Remove one label | `removeLabels` | Leaves the others |
| Set the complete label set | `labels` | Replaces every existing label |
| Link related work | `relatedTo`, `blocks`, `blockedBy` | Append-only, take issue identifiers |
| Attach a URL (PR, dashboard, doc) | `links` | Append-only, `[{url, title}]` |
| Make it a sub-issue | `parentId` | Single parent |

`priority` is numeric and inverted — `0` None, `1` Urgent, `2` High,
`3` Medium, `4` Low — so a lower number means more urgent.

Use `relatedTo` to wire up a multi-repo ticket set as it's created, so each
ticket carries links to its siblings rather than standing alone; see
`references/ticket-templates.md` for the set's shape.

### Title

Write it short, verb-first, and scannable on its own in a list — `Fix
calendar loading bug`, `Add Stripe webhook`, not a full sentence. Keep it
plain — the team prefix (`WAL-`, `ACC-`) already appears on the issue
identifier automatically.

### Description and multi-repo ticket sets

For the description template to use (feature/initiative vs. bug report) and
for creating a linked set of tickets from a multi-repo plan, read
`references/ticket-templates.md`.

### Formatting that reads well in Linear

Write every ticket description and comment in this style by default — new
tickets, template-based tickets and replies alike, without waiting to be asked.
Linear's editor renders full markdown, so a ticket can be scannable rather than
a wall of text. The shared rules are in `${CLAUDE_PLUGIN_ROOT}/references/output-style.md`
"Posted markdown style"; these elements are Linear's own:

| Content | Element | Why it earns its place |
| --- | --- | --- |
| Section headings (`Problem`, `Ask`, `Acceptance criteria`) | `## <emoji> Header` — e.g. `## 🔬 Approach`, `## 📦 Deliverables`, `## ✅ Exit criteria` | Linear gives a real header its own visual weight, and the icon makes the header row scannable at a glance; bold text renders at body size and blends in |
| Sub-sections within a section | `### <emoji> Header` — e.g. `### 🗄️ Repository / data-access layer` | Breaks a long section into labelled blocks instead of bold-only lines |
| Named things the reader scans for (patterns, key types, a flow) | Bold inline — `**Strategy**`, `**branded types**`, `**route → controller → service**` | Picks the key concepts out of a dense bullet |
| A long log dump or stack trace | `+++ <title>` … `+++` collapsible section | Keeps the ticket scannable while the detail stays available |
| Status of a service, check, or environment | The icons from `${CLAUDE_PLUGIN_ROOT}/references/output-style.md` | A reader scans for the one that isn't ✅ |

Two Linear behaviours worth using deliberately:

- **Write a ticket id bare** (`WAL-5674`) and Linear links it *and* adds it as a
  related issue automatically — so mentioning siblings in a description wires up
  the relations without a second `save_issue` call.
- **@mention by display name** (`@johndoe`) to pull a person in; `@` also
  resolves projects, documents and PRs.

Put emoji on headers only — one per `##`/`###`, chosen to name the section's
content — and keep body text plain apart from bolded lead terms. Reserve `---`
rules for structure that genuinely needs separating.

### Restyle an existing ticket

When touching a ticket written before this style (or by someone else) and the
ask is to tidy it, bring it up to the style above by changing markup alone —
headers, emoji, bold — and keep every word as written. Use `patch` with the
section being restyled as `old_string`, one section per operation.

After each `save_issue`, compare the returned `title` and `estimate` with their
values before the call: a description patch has been seen to wrap a
`[Spike]`-style title prefix in backticks and to reset the estimate. Restore
either with a follow-up `save_issue` passing just that field.

### Team, project, estimate, cycle

Resolve all four before calling `save_issue`: team and project from
`references/repo-team-project-map.md` first, then live lookups with
`AskUserQuestion`; cycle always live. Read `references/resolve-fields.md`
before the first `save_issue` that creates a ticket or sets one of them, and in
"Start work on a ticket" step 3.

## Query and report

Use `mcp__linear__list_issues` for anything shaped like "my open WAL tickets,"
"what's in the current cycle," or "unassigned ACC bugs":
- `assignee: "me"` for the current user's tickets, `assignee: null` for unassigned.
- `team`, `state`, `label`, `project`, `cycle`, `priority` narrow the query — pass
  whichever the user's phrasing implies.
- Pass `fields` with only what the report needs — the default response
  includes a truncated `description`, which a list view rarely uses.

Present results as a table: `ID | Title | Status | Priority` at minimum, adding
columns (assignee, project, due date) the request calls for.
- `ID` is a markdown link to the ticket —
  `[ACC-1523](https://linear.app/jeeves/issue/ACC-1523)`. The bare id resolves,
  so the title slug is never needed.
- `Status` shows the state's own name, carrying the icon for its type from the
  Workflow states table above — so `In Review` reads `⏳ In Review` and
  `Production Ready` reads `✅ Production Ready`.

Follow `${CLAUDE_PLUGIN_ROOT}/references/output-style.md` for the shared reporting
vocabulary.

## Draft a reply — match the audience

Every `@jaidev` comment follows the `jaidev` skill. For any other reply or comment, read
`references/replies.md` before drafting: the audience table, section headers and the
approval step before `save_comment`.
