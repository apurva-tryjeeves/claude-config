---
name: release
description: Ship a change in this repo to everyone's jeeves plugin — branch, bump the plugin version, commit, open the PR, squash-merge it, delete the branch and update the jeeves-local marketplace. Trigger on "release", "ship this", "open the PR" or "publish the plugin" in claude-config.
---

# Release a claude-config change

Takes uncommitted edits in this repo to a merged PR on `master` and a refreshed
`jeeves` plugin. Squash-merge and branch deletion run as soon as the PR is
open; the user's "release" is the approval.

## Steps

1. **Branch.** On `master`, create a branch named for the change
   (`docs/<topic>`, `feat/<topic>`, `fix/<topic>`) from an up-to-date `master`:
   ```bash
   git switch master
   git pull --ff-only origin master
   git switch -c docs/<topic>
   ```
   On a feature branch already, stay on it.

2. **Pick the files.** List `git status --short`, then stage only the files
   that belong to this change, by path. Leave unrelated edits (e.g. a
   skill's write-back to `jeeves/skills/mysql/references/schema/`) in the
   working tree and name them in the report. When it's unclear which files
   belong, ask with one `AskUserQuestion`.

3. **Bump the version** when any staged file is under `jeeves/`: raise the
   patch number of `version` in `jeeves/.claude-plugin/plugin.json`
   (`x.y.z` → `x.y.(z+1)`) and stage it. Confirm the branch carries it; this
   prints the old and new lines:
   ```bash
   git diff origin/master -- jeeves/.claude-plugin/plugin.json | grep '"version"'
   ```

4. **Commit** with a subject `<type>(jeeves): <Outcome>` (`docs`, `feat`,
   `fix`, `refactor`, `chore`; plain `<type>:` when nothing under `jeeves/`
   changed), one bullet per change in the body, the new version as the last
   bullet, and the session's co-author trailer.

5. **Push and open the PR** against `master`, with the commit subject as the
   title and a body file in the scratchpad:
   ```bash
   git push -u origin <branch>
   gh pr create --base master --head <branch> --title "<subject>" --body-file <body.md>
   ```
   Body shape (PR #30 is the reference):
   - `> [!NOTE]` headline: the outcome in one or two sentences.
   - `## ❗ Problem`: one bullet per fact.
   - `## 🛠️ Solution`: a `| File | Change |` table, then bullets for
     cross-cutting notes and `Plugin version x.y.z.`
   - `## 🧪 How to test`: `- [x]` checks that were run.
   - The session's PR attribution line.

6. **Squash-merge and delete the branch:**
   ```bash
   gh pr merge <number> --squash --delete-branch
   ```
   When the merge is blocked (failing check, conflict), stop and report the
   reason with the PR link.

7. **Return to `master`** with the merged commit:
   ```bash
   git switch master
   git pull --ff-only origin master
   ```
   Unstaged edits from step 2 travel with the switch and stay uncommitted.

8. **Update the plugin.** Ask the user to run these in the prompt, in order:
   ```text
   /plugin marketplace update jeeves-local
   /reload-plugins
   ```
   Then confirm the new version is installed:
   ```bash
   ls ~/.claude/plugins/cache/jeeves-local/jeeves/
   ```

## Reporting results

Report in one short block:
- the merged PR link and its squash commit on `master`;
- the version, old → new;
- files left uncommitted;
- whether the new version shows under the plugin cache.

Leave out the diff, the PR body and the commands run. A blocked merge leads
the report, with its reason.
