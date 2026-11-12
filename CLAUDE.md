# claude-config

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
