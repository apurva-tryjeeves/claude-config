# Output Style — shared reporting vocabulary

How every `jeeves` skill renders a result. One vocabulary across
skills, so a Jenkins build, a PR check, a Linear ticket and a sync row all read
the same way.

Brevity comes first: answer what was asked, then stop. These rules shape the
answer that remains — they are not a licence to add sections.

## Status icons

Mark every status with its icon, so an outcome reads at a glance.

| Meaning | Icon |
| --- | --- |
| Success, passed, merged, completed | ✅ |
| Failure, error | ❌ |
| Warning, unstable, flaky, degraded | ⚠️ |
| Aborted, cancelled, closed unmerged, blocked | ⛔ |
| Running, in progress, pending, queued | ⏳ |
| Skipped, not applicable | ⏭️ |
| Open, todo, not started | ⚪ |

Jaidev run state is the one exception: it uses the colour circles 🟢 🟡 🔴 ⚪ from the "Color coding" table in `jeeves:jaidev` `references/background-agents.md`.

Git working-tree state uses the glyphs from the user's Starship prompt
(`~/.config/starship.toml`), so the terminal prompt
and a skill's output agree: ⬆️ ahead · ⬇️ behind · 🔀 diverged · ✅ staged ·
📝 modified · ➕ untracked · 📦 stashed · 🗑️ deleted · ➡️ renamed · 🚧 conflicted.

## Link every id that has a URL

Write an id the user may want to open as a markdown link, so it is one click
away rather than a copy-paste:

| Id | Link target |
| --- | --- |
| Linear ticket | `[ACC-1523](https://linear.app/jeeves/issue/ACC-1523)` |
| GitHub PR | `[#534](https://github.com/JeevesInc/<repo>/pull/534)` |
| Jenkins build | `[#44088](<job-url>/44088/)` |
| SonarCloud issue | `[rule-id](https://sonarcloud.io/project/issues?id=JeevesInc_<repo>&open=<key>)` |

The bare Linear id resolves on its own — `linear.app/jeeves/issue/ACC-1523`
redirects to the full slug, so the exact title text is never needed.

## Render machine values as human values

| Raw | Rendered |
| --- | --- |
| Duration in ms (`567000`) | `9m27s` |
| Epoch ms (`1789000000000`) | `10 Sep 5:56am`, in local time |
| Byte counts | `4.2M` |
| A full 36-char uuid in a table cell | the full id — ids stay untruncated |

## Tables for rows, fenced blocks for logs

- **Rows** — one markdown table, one row per record, headers matching the source
  column names. This is the default for every result set, a single row included.
- **Log excerpts** — a fenced block holding the handful of lines that carry the
  meaning, with the surrounding log left out.
- **A verdict line** — lead with icon, outcome, linked id, and duration, then
  put supporting detail below it.

> ✅ **SUCCESS** — [#44088](https://jenkins.dev.tryjeeves.vpn/job/deploy-DEVELOP-environment/44088/) · 9m27s

## Group a long list by what distinguishes it

When a result runs to dozens of near-identical rows (log hits, error lines, sync
failures), report the counts by their distinguishing field and show a sample,
rather than every row:

| Error | Count | First seen |
| --- | --- | --- |
| `exceeded its progress deadline` | 43 | 10 Sep 5:56am |
| `ECONNREFUSED 10.0.4.12:5432` | 6 | 10 Sep 6:02am |

## Posted markdown style (tickets, PR descriptions, comments)

Write every Linear ticket and comment, PR description, PR comment and review
summary in this style. The platform skill adds its own sections and
collapsible form.

- Start each section with `## <emoji> Header` (`###` for a sub-section), one emoji per header, chosen to name the section's content; keep body text plain apart from bolded lead terms.
- Bold the lead term of each bullet or checkbox (`- [ ] **Gap analysis**: current state vs target`).
- Put one distinct fact, cause or symptom in each bullet.
- Use `- [ ]` task lists for acceptance criteria, test steps and follow-ups.
- Use a table for anything with repeating columns.
- Put names, paths and commands in `code`; fence SQL, logs, stack traces, config and command output with a language tag (`text`, `bash`, `sql`).
- Wrap a long log dump in the platform's collapsible: `+++ <title>` … `+++` in Linear, `<details>` in GitHub.

