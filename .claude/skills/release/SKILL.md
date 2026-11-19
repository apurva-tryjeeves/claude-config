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

8. **Update the plugin.** `jeeves` is installed at `local` scope, once per
   JeevesInc project, so it stays out of other repos; each install updates on
   its own.
   1. Ask the user to run this in the prompt, which fetches the new version
      into the marketplace:
      ```text
      /plugin marketplace update jeeves-local
      ```
   2. Update every local install, run in the background (about 2 minutes for
      50 projects):
      ```bash
      python3 .claude/skills/release/scripts/update_local_installs.py
      ```
      It runs `claude plugin update --scope local` inside each project and
      uninstalls the plugin from projects whose folder is gone. Pass
      `--remove <project-path>` to uninstall from a folder that still exists.
      Each failure is listed at the end with its reason, and the run exits 1;
      rerun it to retry.
   3. Ask the user to restart Claude Code (or run `/reload-plugins`) so the
      session loads the new version.

## Reporting results

Report as a table with one row per item, then one **TL;DR** line:

| Item | Result |
|---|---|
| PR | merged PR link and its squash commit on `master` |
| Version | old → new |
| Uncommitted | files left out, or "none" |
| Plugin installs | counts updated / removed / failed |
| Failures | one row per failed project with its reason (omit when none) |

Leave out the diff, the PR body and the commands run. A blocked merge leads
the report, with its reason.
