# Jaidev reference

Observed behaviour of Jaidev ("Jeeves AI Developer", `@jaidev` on Linear),
from real tickets. Check here first; when Jaidev shows something new, update
this file in the same turn.

Sections 1–5 hold stable behaviour and are safe to reuse across runs.
Section 6 holds timings and costs, which vary by ticket — add a column and a
row after every run.

## At a glance

| Fact | Value |
|---|---|
| Linear handle | `@jaidev` |
| Start trigger | New top-level comment, first line exactly `@jaidev start` |
| Status comment title | **Jaidev — <TICKET-ID>** |
| PR author | `jaidev-jeeves` |
| Branch | `jai-dev/<ticket-id-lowercase>` (e.g. `jai-dev/wal-6298`) |
| Implementation attempts | Up to 5 per run, before it posts Blocked |
| PR revision attempts | 3 per PR; each review round uses one, SonarCloud findings included |
| GitHub token scope | Pushes code; `.github/workflows/*` goes through a human |

Develop environments per team, from Jaidev's deploy comment. For a team with
no row, read its deploy comment, then add a row.

| Team | Shared develop environments |
|---|---|
| Wallet | develop-11, develop-12, develop-13, develop-20 |

## Contents

1. Lifecycle
2. Commands
3. Triggering a run
4. What its comments look like
5. Limits
6. Timings and costs

## 1. Lifecycle

1. **Start**: a user posts `@jaidev start` as a new top-level comment.
2. **Analysis**: Jaidev reads the ticket, its comments and its knowledge base
   (`PRODUCT.md`, `PLATFORM.md`, `SERVICE.md`, one file per repository) and
   explores the repositories.
3. **Questions** (optional): it posts questions and waits. Status shows
   "Gathering Info (Waiting for Answers)".
4. **Plan**: it posts an "Implementation plan" comment and waits for
   approval. Feedback in the plan thread gets an in-thread ack within ~10 s;
   Jaidev then resolves that thread and posts "Implementation plan (v2)" as a
   new top-level comment.
5. **Implementation**: after approval it posts a live progress comment per
   repository and keeps it updated. When the base branch moves, it merges the
   base into its branch. It then opens one PR per repository, cc'ing the user
   who started it.
6. **Blocked** (optional): when it can't meet a definition-of-done item, it
   uses up its attempts (up to 5), then posts "## 🚫 Blocked — Needs Human
   Help" and waits for `@jaidev resume`.
7. **Review**: GitHub PR review comments trigger a revision ("Revision #1 —
   addressing N new comment(s) — Attempt 2/3"). SonarCloud bot findings
   trigger one too, with no human comment. It explains each fix in a PR
   comment.
8. **Deploy** (optional): on request it deploys to a shared develop
   environment or a short-lived one.
9. **Complete**: after the merge, the status comment shows "Complete ✅".

Throughout, the status comment shows the status, who started it, cost per
phase, repositories, PR links and a timeline.

## 2. Commands

| Command | Where | Effect |
|---|---|---|
| `@jaidev start` | New top-level comment | Starts analysis |
| Reply text | In the question's thread | Answers a question |
| `@jaidev skip` | Ticket comment | Skips open questions |
| `@jaidev abort` | Ticket comment | Stops the run |
| `@jaidev plan:approved` | Reply in the latest plan's thread | Approves the plan, starts implementation |
| `@jaidev plan:approved, auto-deploy` | Reply in the latest plan's thread | Approves and provisions a dev environment |
| Feedback text | Reply in the latest plan's thread | Requests plan changes; Jaidev acks in ~10 s, resolves the thread, posts the revised plan as a new top-level comment |
| `@jaidev plan:drop <repo-name>` | Reply in the latest plan's thread | Removes a repository from the plan |
| `@jaidev resume` | Reply in the Blocked thread | Resumes a blocked run; it reads the context text after the command |
| `@jaidev deploy on develop-NN` | Ticket comment | Deploys the ticket's modules to a shared develop environment (`to` and `on` both work) |
| `@jaidev deploy` | Ticket comment | Provisions a short-lived environment `dev-jaidev-<linear-id>`; re-run after pushing changes |

## 3. Triggering a run

- Start every run with a **new top-level comment** whose first line is
  exactly `@jaidev start`. The full briefing follows in the same comment. A
  fresh comment starts the run within seconds (3 s on WAL-6298).
- Jaidev responds to that exact wording. These variants left it idle:
  `start @jaidev`, `@jaidev get started`, `@jaidev please pick up this
  ticket…`.
- To retrigger, post a fresh comment. Jaidev reads new comments only; a
  comment edited to begin `@jaidev start .` stayed idle for 85 min.
- Assignment alone leaves Jaidev idle — it replies "I don't pick up tickets
  via assignment anymore. Reply `@jaidev start`".
- "Started by" in the status comment names the Linear account that posted
  the start comment.

## 4. What its comments look like

**Status comment** values seen: "Analyzing... (Queued — waiting for
available worker)" (first value when every worker is busy), "Awaiting Plan Approval", "Implementing...
(<repo> · verifying)", "Blocked 🚫 (Needs Human Help)", "PRs Created
(Awaiting Merge)", "Addressing PR Feedback..." (repo phase `revising`), "Complete ✅". The cost line is split by phase ("Analysis
· Planning · Impl · PR Rev") and refreshes after implementation ends. Earlier
phase figures can rise later (WAL-6300: analysis $0.15 → $0.27 by the time
implementation started), so read final costs from the last status.

**Implementation plan** sections:

- Header: Complexity, Estimate (points), Repos, Confidence, Delegating User
- Summary
- Key Assumptions, each with the evidence it checked (omitted from v1 on
  WAL-6300, a briefing that listed every file and line)
- Affected Services table: service, base branch, changes
- Implementation Sequence per repository, with "Done when" criteria
- Feature Flags
- Risk Assessment: risk and mitigation pairs
- Cross-Cutting Invariants it verifies before opening a PR
- Context Sources: knowledge-base files and repositories explored
- Footer with the approval commands

When reviewing, focus on Key Assumptions (they carry the most risk), whether
Affected Services lists the right repository and base branch, and whether the
"Done when" items match the ticket's acceptance criteria.

**Revised plan**: titled "Implementation plan (v2)". It lists the changes
either as a "Changes in this revision" list or as numbered items inside the
Summary (WAL-6300). It may omit Key Assumptions and shorten Context Sources.

**Live progress comment** (during implementation): it opens as
"**<repo>** • `jai-dev/<id>` ↗ / ⏳ Cloning `<base>`…", then shows "**<repo>** •
`jai-dev/<id>` ↗", a phase bar "Setup → Implementing → **Verify** → PR",
three rolling notes, and "🔄 N files • N edits • N min • attempt x/5". The
rolling notes surface blockers before the Blocked comment does.

**Blocked comment**: "## 🚫 Blocked — Needs Human Help" with What Failed,
What I Tried (per attempt), Root Cause Assessment, What I Need From You, and
To Resume. Read the cause from What Failed and What I Tried; the root-cause
line can read "Unknown (low confidence)" when the cause is stated above it.

**PR result comment**: "**<repo>** • ✅ Complete, PR #N • N files • $ • N
min", with revision entries appended. The file count covers the last
session only; read the PR for the full list.

**Deploy comment** after the PR: lists the module to deploy and the team's
allocated develop environments (see At a glance).

## 5. Limits

- It needs an existing base branch with at least one commit; the first commit
  of a new repository is a manual step.
- Deploys need the service to exist in the develop environments (Helm chart,
  HelmRelease).
- Knowledge-base files cover existing repositories. For a new repository
  Jaidev explores the code directly, so give the briefing extra context.
- Its GitHub token pushes code only; `.github/workflows/*` changes reach the
  branch through a human. A briefing that puts a workflow change in its
  definition of done ends Blocked.
- It runs one bounded single-file test process at a time and leaves the full
  suite and coverage thresholds to CI. It reports a briefed "run the full
  `npm test` and paste its summary" item as not done, even in an approved
  plan. Brief the full-suite result as "CI `test / Unit Test` passes" instead.
- A blocked run retries up to 5 times before reporting, and each attempt
  costs money whether or not anything changed.
- Each phase costs money (shown in the status comment). Clear briefings avoid
  question rounds, plan revisions and blocks.
- Open question: whether a reply during implementation stops the retries.
  Record the answer here once a run shows it.

## 6. Timings and costs

Provisional — two runs so far. Add a column per run to the timing table and a
row per run to the cost table.

Queue wait is logged apart from the phase timings. The status timeline has no
entry for leaving "Queued"; read it from Jaidev's logs on the dev OpenSearch
cluster (index `logs-YYYY.MM.DD`, `namespace_name: jai-dev-preprod`, `log`
containing the ticket ID). "Enqueued ticket-received message" marks the start
of the wait and "Processing ticket-received message" its end. Without log
access, check the status comment about 5 s and 20 s after posting.

| Event | WAL-6298 | WAL-6300 |
|---|---|---|
| `@jaidev start` → status comment | 3 s | 3 s |
| Queued → analysis started | not queued | 0.005 s (status left "Queued" at +0.2 s) |
| → analysis complete | 23 s | 17 s |
| → plan v1 | 3 min 30 s | 4 min 6 s (analysis complete 13:31:13 → plan 13:35:19) |
| Plan feedback → in-thread ack | 11 s | 9 s |
| → plan v2 | 1 min 25 s | 55 s |
| `plan:approved` → progress comment | 5 s | 12 s (approval logged at +2 s; plan thread resolved at +3 s) |
| → PR opened, or Blocked | 19 min (Blocked: workflow scope) | 4 min 30 s (PR, no block) |
| `@jaidev resume` → PR opened | 2 min 38 s | — |
| SonarCloud findings → fix pushed | ~6 min | — (Sonar clean) |
| Human PR review → revision started | — | 14 s |
| Revision started → fix pushed | — | 2 min (+ PR reply 8 s later) |

| Ticket | Kind | Analysis | Planning | Impl | PR rev | Total | Notes |
|---|---|---|---|---|---|---|---|
| WAL-6298 | Config only | $0.30 | $1.69 | $6.56 | $0.63 | $9.18 | 1 plan revision; 1 block ($6.25 of impl); 1 SonarCloud revision |
| WAL-6300 | Code + tests, 25 files | $0.27 | $2.37 | $0.50 | $0.20 | $3.35 | 1 plan revision ($0.33); 0 blocks; 1 human review revision; queue wait 5 ms |
