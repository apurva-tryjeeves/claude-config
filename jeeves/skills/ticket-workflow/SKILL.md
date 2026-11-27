---
name: ticket-workflow
description: Coordinate one Linear sub-ticket from drift check to close-out through the ticket agents (drift checker, designer, implementer, closer) and restack ticket branches with the stack rebaser. Trigger on starting, building or picking up a sub-ticket ("start ACC-1747", "build this ticket", "next ticket"), rebasing a ticket stack, or closing a ticket out.
---

# Ticket workflow

You are the coordinator. The agents read, design, build and draft; you take every outward action (Linear saves, pushes, PRs, Slack) after the user's yes.

## Flow

```text
ticket-drift-checker → ticket-designer → (user approves; optional principal-engineer review)
  → ticket-implementer → (user approves PR title/body; coordinator pushes and opens the PR) → ticket-closer
stack-rebaser whenever a parent or base branch moves
```

Load `jeeves:linear` and run its "Start work on a ticket" steps before launching the first agent.

## Gates

Wait for the user's explicit yes at each of these:

| Gate | Show the user |
|---|---|
| Design | The design file and its open questions; implementation starts from the user's answers |
| Implementer launch | One `AskUserQuestion` for model and effort, with the options in the agent's description |
| PR | 3–4 titles and the body, per `jeeves:git-preferences` "Create a PR" |
| Every Linear save | The drift checker's `Changes` list and new description; the outcome comment; each state change |
| Every force-push | The stack rebaser's push commands and per-branch report |

## Agents

Start each with `jeeves:<name>`. Every brief carries the ticket id and repo path, plus its row's fields; each agent returns a fixed report.

| Agent | Brief adds | Check before relaying |
|---|---|---|
| `ticket-drift-checker` | Branch to compare, design-doc sections | The draft file exists |
| `ticket-designer` | Parent branch, design doc, decisions so far | Design file exists; `git -C <worktree> log -1` matches the reported SHA |
| `ticket-implementer` | Parent branch, design path, the user's answers, the session's `Co-Authored-By` trailer | `git log -1`, `git status --short` clean, branch ahead of `origin/<parent>` by one commit, `git ls-remote origin feat/<TICKET>` matches what it printed before the launch |
| `stack-rebaser` | Parent branch, new base, open sub-branches in order, conflict decision list | Each reported new SHA exists locally; `git ls-remote` shows every remote tip still at its old SHA |
| `ticket-closer` | Merged PR number, parent PR number | Draft files exist; `gh pr view <n> --json state` is `MERGED` |

- `jeeves:principal-engineer` gives the optional independent design or PR review; `jeeves:jeeves-verifier` verifies after a dev deploy.
- Keep the number of background agents within the limit in `${JEEVES_MEMORY_DIR:-$HOME/.claude/memory}/agent-delegation.md`, when that file exists.

## Branches

Sub-ticket branches follow `jeeves:git-preferences` `references/parent-ticket-branches.md`. A stacked parent (a parent branch cut from another parent branch) opens its PR against that parent; once that parent merges, retarget the PR to the default branch. Worktree layout and per-repo commands live in `${CLAUDE_PLUGIN_ROOT}/references/repo-dev-setup.md`.

## Reporting results

After each agent: one status line (icon per `${CLAUDE_PLUGIN_ROOT}/references/output-style.md`), what you checked, and the next gate with what the user must approve. Leave out the agent's full report, restated context and closing offers.
