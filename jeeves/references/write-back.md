# Write-back to the source clone

The rule every skill follows when it records a fact in one of its own files
(a repo map, a schema note, a confirmed-env row, a saved query, a secret path).

| Item | Value |
|---|---|
| Clone path | `${JEEVES_PLUGIN_SRC:-$HOME/github/apurva-tryjeeves/claude-config}` |
| Installed copy | replaced on every plugin update, so a fact written there is lost |

## Read

- Read the clone's copy of the fact file when the clone directory exists; read the installed copy otherwise.

## Write

- Edit the clone's copy as it stands on disk, on its current branch, in the same turn the fact is learned.
- Run no `pull`, `switch`, `reset` or `stash` in the clone.
- Leave the edit uncommitted and tell the user it is ready to review and push.
- When the clone directory is absent, report the fact and the edit (file, before, after) in the reply.

## Open a PR against claude-config

- Work in a separate `git worktree` cut from `origin/master`; leave the clone's checkout untouched.
- Bump the patch `version` in `jeeves/.claude-plugin/plugin.json` before `gh pr create`.
