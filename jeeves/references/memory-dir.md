# Memory directory

Where skills keep per-person files that change with every run, such as timing samples. They stay on each person's machine, outside the plugin.

| Item | Value |
|---|---|
| Directory | `${JEEVES_MEMORY_DIR:-$HOME/.claude/memory}` |
| Set it | `env` in `~/.claude/settings.json`, e.g. `"env": { "JEEVES_MEMORY_DIR": "~/.claude/memory" }`, so every Bash call a skill makes sees it |

| Skill | File |
|---|---|
| `git-preferences`, `jaidev` | `ci-check-timing.md` (`$JEEVES_CI_TIMING` overrides this one file) |
| `ticket-workflow` | `agent-delegation.md` (background-agent limit; read only) |
| `jenkins` | `jenkins-deploy-timings.md` |
| `jaidev` | `jaidev-run-timings.md` |

- Resolve the directory once per session, then read and write the files there:

  ```bash
  echo "${JEEVES_MEMORY_DIR:-$HOME/.claude/memory}"
  ```

- When a skill creates one of these files, add a one-line entry to that directory's `MEMORY.md`: gist plus trigger.
- Point `JEEVES_MEMORY_DIR` at the same folder as your `autoMemoryDirectory` when you set one, so these files load with your other memories.
