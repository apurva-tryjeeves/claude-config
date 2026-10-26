# Jaidev reference

Observed behaviour of Jaidev ("Jeeves AI Developer", `@jaidev` on Linear),
from real tickets. Check here first; when Jaidev shows something new, update
this file in the same turn.

Sections 1–5 hold stable behaviour and are safe to reuse across runs.
Section 6 points to the local file that holds timings and costs, which vary
by ticket.

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
| Accounting & ERP | develop-07 |

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
- The start comment loses identifiers, inline backticks and fenced code
  (WAL-6301, ACC-1588, ACC-1638). Thread replies and plan feedback arrive intact.
  Keep the start comment to prose and short lists, send names and code as the
  answer in Jaidev's question thread or as plan feedback, and ask it to quote key
  lines back.
- Implementation works from the plan's text (WAL-6301): code that must land verbatim
  goes in the plan in full, so ask Jaidev to include it.
- With `collectCoverage: true` and a global threshold in `jest.config.js`, a
  single-file `npx jest <file>` run fails the threshold even when its tests
  pass. Brief single-file runs with this command; a bare path under
  `--selectProjects unit` runs the whole suite (2,241 tests on accounting-service):

  ```bash
  npx jest --ci --coverage=false --runTestsByPath <file>
  ```
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
- Its sandbox has no Docker. A unit-test project whose `globalSetup` starts a
  database container needs Docker; brief tests that mock the DB layer
  and leave the full run to CI.
- On a parent feature, Jaidev merges a moved base into its branch by default
  (ACC-1637, ACC-1638). A PR comment asking it to rebase onto the parent works:
  on ACC-1591 it replied in about 2 minutes, rebased with no conflicts,
  force-pushed and ran ts-lint and build. The request counts as a revision round
  ("Revision #3" there, the last of 3 attempts).
- A second PR into the parent can be refused with "Base branch was modified"
  right after a sibling PR merges (ACC-1630 and ACC-1633). One retry works when the
  files differ.
- It marks DB-backed tests it cannot run as environment-blocked (no Docker or
  database in its sandbox); CI `test / Unit Test` settles them.
- Its plan can raise the estimate (ACC-1633: 1 to 2 points) and the new value
  overwrites the Linear estimate.
- After the PR it posts a "Deploy this ticket" comment. The user deploys; agents
  leave the comment unanswered and run no `@jaidev deploy`.
- A correction posted while Jaidev is already writing the next plan version can be missed: on ACC-1636 plan v2 was posted before it read the correction in the v1 thread. Repeat the correction in the v2 thread (the next plan then carries it).
- Plan code blocks can carry literal `\n` text (ACC-1645 plan v2). Check the opened PR's source for stray `\n` sequences.
- The doc-format hook requires `## <emoji>` section headers in GitHub
  approval bodies and Linear comments; comments starting with `@jaidev`
  are exempt.

## 6. Timings and costs

Kept outside the plugin, in `~/.claude/memory/jaidev-run-timings.md`. Read it
to estimate a run and add the new run's row to its cost table when it closes out.
