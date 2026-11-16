# Resolve team, project, estimate and cycle

Read before the first `save_issue` that creates a ticket or sets a team,
project, estimate or cycle, and during "Start work on a ticket" step 3.

Resolve all four before calling `save_issue`. Team and project are largely
stable per repo — check `repo-team-project-map.md` first for a
repo already seen; a hit there skips both the live lookup and re-asking the
user something they already answered. Cycle is never stable enough to cache
(it rolls over roughly every two weeks), so always resolve it live regardless
of what's in the reference file.

Read `repo-team-project-map.md` and, after the user confirms a repo's
team/project (via `AskUserQuestion` or otherwise), add or update that repo's
row in it, following `references/write-back.md` at the plugin root.

For anything not already covered by the reference file, fetch the real
options first, then ask with `AskUserQuestion` so the user picks from what
actually exists rather than a guessed or remembered value. Team, project,
and cycle are all workspace state that changes over time (teams get added,
projects start and complete, cycles roll over) — call the relevant
`mcp__linear__list_*` tool fresh, in this same turn, every time you resolve
one live, rather than reusing a list fetched earlier in the conversation or
from a past run of this skill.

- **Team**: check the repo map, then the "Common teams" table in `SKILL.md`, for
  the fast path. If genuinely ambiguous (e.g. a cross-cutting ticket) or
  neither covers it, call `mcp__linear__list_teams` fresh. The workspace has
  ~28 teams — well past `AskUserQuestion`'s 4-option cap — so narrow first:
  use its `query` param with a keyword from the request (repo name, product
  area) to shortlist ≤4 candidates for `AskUserQuestion`. If the keyword
  doesn't narrow well (multiple plausible teams, or none), skip
  `AskUserQuestion` and instead print the full team list as a table in chat,
  asking the user to name the one they mean.
- **Project**: check the reference file for the repo first. If it lists a
  known project, confirm it's still what the user wants (a repo can move to
  a new project over time) rather than silently reusing a stale entry. If
  the repo isn't in the reference file yet, fetch active initiatives with
  `mcp__linear__list_projects` (`team: <team>, state: "started"`) — a single
  active team can easily have
  10-30+ open projects, so narrow the list before `AskUserQuestion`: use `query` with a keyword from the ticket title/description,
  or filter the fetched list yourself by relevance, down to ≤3 real
  candidates, then ask via `AskUserQuestion` with those plus a "No project"
  option (4 options in all) — confirm the match with the user rather than taking the top result
  silently, and fetch a fresh project list for each new ticket in the
  session. When narrowing still leaves more than 4 plausible matches (or
  nothing narrows well), fall back to printing the full project list as a
  table in chat and asking the user to name or number their pick, rather
  than truncating the options silently.
- **Estimate** (story points): this workspace uses a points scale (`1`, `2`,
  `3`, `5`, `8`, …), not a time estimate. Ask via `AskUserQuestion` with
  `1`, `2`, `3`, `5` as the four options — the automatic "Other" covers `8`,
  larger values and "No estimate" — unless the user already gave a number.
- **Cycle**: `mcp__linear__list_cycles` takes the team's UUID, not its name —
  take it from `get_issue`'s `teamId` or from `list_teams`. Fetch
  `list_cycles` (`teamId: <uuid>`, `type: "current"`) fresh, then ask via `AskUserQuestion` offering the current cycle by its
  actual returned name (cycle names/dates roll over roughly every two weeks,
  so take the name from the fetch, never from a previous session) alongside
  "Backlog (no cycle)" — default to suggesting the current cycle for work
  starting now, but let the user pick.

These four can go in one `AskUserQuestion` call (multiple questions at once)
once the options for each are fetched.
