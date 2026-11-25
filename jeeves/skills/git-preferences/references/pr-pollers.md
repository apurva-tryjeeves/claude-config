# PR Post-Create Polling

After creating a pull request, or pushing to a branch that already has an open PR, ask before starting any background poller. Each poller runs per-PR and stops itself.

## Ask which poller(s) to start

Call `AskUserQuestion` (multiSelect) offering **Comments poller** and **Checks poller**, and start only the one(s) picked.

## Comments poller

Watches for review/PR comments that need a response.

- Cadence: every 2 hours, 10:00–22:00 in the user's local time. Create it with `CronCreate` using `0 10-22/2 * * *` — cron fires in the machine's local timezone, so the window follows the user.
- On a new comment needing a response (review comment, requested change, question), notify with a summary.
- On-demand: when asked "any PR comments?", pull status immediately regardless of schedule.
- Stop when the PR is merged or closed.
- Detect new comments by diffing all three sources against the last check — conversation comments and review summaries:
  ```bash
  gh pr view <n> --repo JeevesInc/<repo> --json state,comments,reviews
  ```
  and inline code-review comments, which live on a separate endpoint paged at 30 — `--paginate` returns all of them:
  ```bash
  gh api --paginate repos/JeevesInc/<repo>/pulls/<n>/comments --jq '.[] | {id, user: .user.login, path, line, body, created_at}'
  ```

## Checks poller

Watches CI/check status until it settles.

- Cadence is per-repo. When `${JEEVES_MEMORY_DIR:-$HOME/.claude/memory}/ci-check-timing.md` exists, look there for a row matching the target repo; when one exists, use its `First check`/`Interval` columns directly.
- For a repo with no row yet, or no table yet, derive the cadence from that repo's own CI history with a background `Agent` instead of asking the user. Pull the last 10 successful PR runs of each PR-check workflow:
  ```bash
  gh run list --repo JeevesInc/<repo> --workflow <file> --status success --event pull_request --limit 10 --json createdAt,updatedAt \
    --jq '[.[] | ((.updatedAt|fromdateiso8601) - (.createdAt|fromdateiso8601)) | select(. < 7200)] | "n=\(length) min=\(min)s max=\(max)s mean=\(add/length|floor)s"'
  ```
  Time only the long-pole workflow, the slowest PR-check workflow; faster workflows and non-Actions checks (SentinelOne CNS scans) leave the cadence unchanged. Copy the check names from a recent PR's rollup (`gh pr view <n> --json statusCheckRollup`): repos on the shared `infra-reusable-workflows` unit-test workflow prefix each job with `test / `, and jeeves-web uses unprefixed names.
  Set `First check` a little under the fastest duration and `Interval` from the spread between fastest and slowest, then add the row (repo, long-pole workflow, check name, min/max/mean, sample size, first check, interval) per **Write back a timing row** below, and start polling once the agent reports back.
- After checks settle, if the actual settle time differs noticeably from the remembered cadence, refine that repo's row in the same turn, per **Write back a timing row**.
- Start the poller by invoking the `loop` skill with no interval (dynamic mode), passing the
  poll prompt: the PR, the repo, its `First check` and `Interval` from the timing row, and the
  `Settles on` checks. Each tick then schedules the next one with `ScheduleWakeup`. Use this for
  "run in the background" too; a hand-written shell loop or `Monitor` replaces it only when the
  user asks for one.
- Several PRs: one poller per PR, each on its own repo's `First check` and `Interval`.
- Poll with `statusCheckRollup`, which exits 0 while checks are still running:
  ```bash
  gh pr view <n> --repo JeevesInc/<repo> --json statusCheckRollup --jq '.statusCheckRollup[] | {name, status, conclusion}'
  ```
- Stop once every check has `status: COMPLETED` **and** every check in the row's `Settles on` column is in the list — on repos using the shared unit-test workflow that is `test / Scan for secrets` and `SonarCloud Code Analysis`. The workflow creates `test / Code Analysis` and `test / Scan for secrets` only after the job before them finishes, so an all-COMPLETED list missing them is mid-handoff — keep polling. Then report per **Reporting results** below.
- A failing check here often traces back to the SonarCloud quality gate — see the `jeeves:sonar-proactive-rules` skill for what triggers it, and `/jeeves:sonar-fix` to clear it.

## Write back a timing row

The table lives in your org memory, outside the plugin, at
`${JEEVES_MEMORY_DIR:-$HOME/.claude/memory}/ci-check-timing.md`, so each person's samples
build up locally.

Add or refine the repo's row there. When the file doesn't exist yet, create it with the first row, a `reference` memory frontmatter (`name: ci-check-timing`) and the table header `| Repo | Long-pole workflow | Check name | Settles on | Min | Max | Mean | Sample size | First check | Interval | Known failures |`, then index it in `${JEEVES_MEMORY_DIR:-$HOME/.claude/memory}/MEMORY.md`.

- **Known failures:** checks that fail on every head for a known reason, comma-separated (jeeves-web: `Validate Localization` until the Crowdin push). Add a check in the same turn its reason is confirmed, and remove it the first time it passes.

## Reporting results

**Checks poller:**

- **Lead with the PR** — its number as a link, carrying the state icon:
  `✅ [#534](https://github.com/JeevesInc/<repo>/pull/534) merged`.
- **Table the checks** — columns `Check`, `Status` (icon + conclusion) and
  `Duration` (human-readable, `4m12s`), one row per check.
- **On a failure, list only the failing checks** and fence the handful of log
  lines naming the cause; the passing ones stay off the table.
- **While checks still run**, give elapsed against the expected settle time from
  the timing row, when the repo has one: `⏳ 2m10s elapsed · ~6m expected`.
  Without a row, give the elapsed time alone.

**Comments poller:**

- **Lead with the PR** as a link and the count of new comments.
- **One bullet per new comment** — author, `file:line` for inline comments, and
  a one-line summary of what it asks for.
