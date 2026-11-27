# claude-config

The `jeeves-local` Claude Code marketplace: one plugin, `jeeves`, with the
skills, agents, scripts and shared references for JeevesInc engineering work.

## Layout

| Path | Holds |
|---|---|
| `.claude-plugin/marketplace.json` | Marketplace entry for the `jeeves` plugin |
| `jeeves/.claude-plugin/plugin.json` | Plugin name, version, description |
| `jeeves/skills/<name>/` | `SKILL.md`, on-demand `references/*.md`, `scripts/` with tests |
| `jeeves/agents/*.md` | Subagents: tools, model, effort, preloaded skills |
| `jeeves/references/` | Shared `output-style.md`, `write-back.md`, `queries.md`, `memory-dir.md`, `doc-spine.md`, `repo-dev-setup.md` |
| `jeeves/bin/`, `jeeves/lib/` | `jsql`, `jsql-pull-secrets`, `jenkins-api`, `jeeves-sync-repos` |

## Scope

- Keep JeevesInc-specific skills and agents here; personal skills live in
  `~/.claude/skills`.
- Name plugin skills and agents `jeeves:<name>`; write plugin paths as
  `${CLAUDE_PLUGIN_ROOT}/…` and skill paths as `${CLAUDE_SKILL_DIR}/…`.

## Editing

- Keep each `SKILL.md` lean: a `description` with what it does and when to
  trigger, and long material in `references/` behind a one-line gist and trigger.
- Give each fact one home and point to it from elsewhere. Reporting vocabulary
  lives in `jeeves/references/output-style.md`, the write-back rule in
  `jeeves/references/write-back.md`.
- When a file moves or a fact changes, update every place that names it: other
  skills, agents, the README "Contributing" table, and the `marketplace.json`
  and `plugin.json` descriptions.

## Python scripts

Stdlib-only Python 3.11, mypy-strict, ruff-clean, with `unittest` tests. Read
`jeeves/agents/jeeves-python-engineer.md` for the full standards before writing
or reviewing a script. Run the checks from the skill's `scripts/`:

```bash
python3 -m unittest discover -s tests -v
uvx ruff check . && uvx ruff format --check .
uvx mypy .
```

## Pull requests — bump the plugin version

Every PR that changes anything under `jeeves/` bumps the patch number of
`version` in `jeeves/.claude-plugin/plugin.json` (`x.y.z` → `x.y.(z+1)`). Once
it merges, `/plugin marketplace update jeeves-local` brings the new version to
everyone (README → "Contributing, and keeping what skills learn").

Before `gh pr create`, confirm the branch carries the bump; this prints the old
and new `version` lines:

```bash
git diff origin/master -- jeeves/.claude-plugin/plugin.json | grep '"version"'
```

When it prints nothing, bump the version, commit it, then open the PR.

For the full flow — branch, commit, PR, squash-merge, plugin update — use the
project skill `.claude/skills/release/SKILL.md`.
