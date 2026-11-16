---
name: sync-repos
description: Fast-forward every JeevesInc repo's default branch from origin without changing what each repo has checked out. Trigger when the user asks to update, sync or pull development across all repos. Rebasing one feature branch goes to git-preferences.
---

# Sync repos

Run `jeeves-sync-repos` with `run_in_background`, then report once it exits.
To rebase one feature branch onto its default branch, use `jeeves:git-preferences`.

## Reporting results

- Lead with a verdict line: `✅ <n> updated · ⏭️ <n> skipped · ❌ <n> failed`.
- Table only the skipped and failed repos: repo, branch, the reason as git printed it.
- Leave out the repos that updated cleanly, and add no follow-up offer.
