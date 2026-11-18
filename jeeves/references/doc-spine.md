# Document spine

The shared section set for what Jeeves skills post: Linear tickets, PR descriptions and
Notion design docs. Each template picks its sections from this table, keeps this order
and uses these headers word for word. How the text looks (bold lead terms, checkboxes,
code, tables) lives in `${CLAUDE_PLUGIN_ROOT}/references/output-style.md`
"Posted markdown style".

## Sections, in order

| Header | Holds | Linear ticket | PR | Design doc |
|---|---|---|---|---|
| `## ❗ Problem` | One bold-lead bullet per distinct fact or cause | ✓ | ✓ | ✓ |
| `## 🎯 Goal` | What success looks like, in one or two sentences | ✓ | — | ✓ |
| `## 📐 Scope` | In-scope bullets, plus an `**Out:**` line when the edge is ambiguous | When ambiguous | — | ✓ |
| `## 🛠️ Solution` | One bold-lead bullet per decision, stated as the behaviour it gives | Optional | ✓ | ✓ |
| `## ✅ Acceptance criteria` | `- [ ]` checks a reviewer can verify | ✓ | — | ✓ |
| `## 🚦 Rollout` | Gates, deploy steps, what to watch, rollback | — | When needed | ✓ |
| `## ❓ Open questions` | Numbered questions, each with an owner | ✓ | — | ✓ |
| `## 🔗 References` | Bold-lead links: ticket, parent, design doc, related work | ✓ | ✓ | ✓ |
| `## 🧪 How to test` | `### 🤖 Automated` `- [x]` items, `### 🧑‍🔬 Manual` `- [ ]` steps | — | ✓ | — |

## Rules

- **One header, one meaning:** a section named above always carries that header and
  emoji. A section only one artifact has (a PR's `🔍 Code review`, a post-mortem's
  `🕒 Timeline`) keeps an emoji that no spine section uses, in the place its template
  gives it.
- **Keep what has content:** include a section when this artifact has something to say
  in it, and keep the table's order for the sections kept.
- **Hand off between artifacts:**
  - The ticket's Acceptance criteria become the PR's `🧑‍🔬 Manual` steps, one per
    criterion, each with its expected result.
  - The design doc's Solution becomes one opening line in the PR's Solution that
    links the doc.
  - The PR and the design doc name the ticket under References.

## Templates

| Artifact | Template |
|---|---|
| Linear ticket shapes | `${CLAUDE_PLUGIN_ROOT}/skills/linear/references/ticket-templates.md` |
| PR title and body | `${CLAUDE_PLUGIN_ROOT}/skills/git-preferences/references/pr-description.md` |
| Notion design doc | `${CLAUDE_PLUGIN_ROOT}/skills/notion-templates/references/design-doc.md` |

Jaidev briefings follow the `jaidev` skill, and Slack release updates follow
`release-notify`; each keeps its own format.
