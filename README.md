# claude-config

Shared Claude Code plugin marketplace for JeevesInc. Distributes team-wide skills
and agents via the `jeeves-shared` plugin so they install the same way for everyone,
instead of being symlinked in by hand.

## Install

From any JeevesInc repo, inside a `claude` session:

```
/plugin marketplace add JeevesInc/claude-config
/plugin install jeeves-shared@claude-config
```

Restart or reload Claude Code if prompted. Once installed, the plugin's skills
and agents are available in every session without further setup.

## Update

```
/plugin marketplace update claude-config
```

Re-run `/plugin install jeeves-shared@claude-config` if a new version needs to be
picked up explicitly.

## What's inside

```
plugins/jeeves-shared/
├── .claude-plugin/plugin.json   # plugin manifest
├── skills/                      # shared skills (one directory per skill, each with a SKILL.md)
└── agents/                      # shared subagents (one .md file per agent)
```

## Contributing

- Add a new skill under `plugins/jeeves-shared/skills/<skill-name>/SKILL.md`.
- Add a new subagent under `plugins/jeeves-shared/agents/<agent-name>.md`.
- Skills must not contain hardcoded personal values (Slack channel IDs, usernames,
  specific Notion page IDs, etc.) — generalize them so any team member can use them.
- Open a PR against this repo; once merged, teammates pick up changes via
  `/plugin marketplace update claude-config`.
