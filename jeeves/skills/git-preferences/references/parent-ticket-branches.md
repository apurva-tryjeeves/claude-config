# Parent ticket whose sub-issues ship together

When a Linear parent ticket's sub-issues go live together (e.g. `ACC-1555` with sub-issues `ACC-1557`, `ACC-1561`, …), collect them on one integration branch named after the parent, and ship that branch to the default branch as one PR. A ticket without such a parent branches off the default branch as in `SKILL.md` → Branch Strategy.

- Give each phase of a design doc one parent ticket and one PR; keep the doc's step numbers (4.1–4.4) as sections of that PR, not as tickets.
- Make work that ships on its own timeline a standalone ticket with blocked-by relations: another repo, a DevOps change, or a removal behind a release gate.

| Branch | Created from | PR base | Merge |
|---|---|---|---|
| `feat/<PARENT>` (e.g. `feat/ACC-1555`) | the default branch | the default branch, once every sub-issue is in | Squash |
| `feat/<SUB>` (e.g. `feat/ACC-1557`) | `feat/<PARENT>` | `feat/<PARENT>` | Squash |

1. Show the parent branch name, then wait for the user's yes. Then create and push the parent branch once, from the updated local default branch:
   ```bash
   git switch <default-branch>
   git pull --ff-only origin <default-branch>
   git switch -c feat/<PARENT>
   git push -u origin feat/<PARENT>
   ```
2. Start each sub-ticket from the updated local parent branch:
   ```bash
   git switch feat/<PARENT>
   git pull --ff-only origin feat/<PARENT>
   git switch -c feat/<SUB>
   ```
3. Open each sub-ticket PR against the parent branch, titled with the sub-ticket's id (see `SKILL.md` → **Create a PR**):
   ```bash
   gh pr create --repo JeevesInc/<repo> --base feat/<PARENT> --head feat/<SUB> \
     --title "feat: [<SUB>] - <description>" --body-file <body.md>
   ```
4. Keep the parent branch current by rebasing it onto the default branch, then rebase every open sub-branch onto the new parent tip. Record the parent's tip before the rebase, so each sub-branch replays only its own commits:
   ```bash
   git switch <default-branch>
   git pull --ff-only origin <default-branch>

   git switch feat/<PARENT>
   OLD_PARENT=$(git rev-parse feat/<PARENT>)
   git rebase <default-branch>
   ```
   Confirm with the user before each force-push — the parent branch carries every merged sub-PR and is the base of every open one:
   ```bash
   git push --force-with-lease origin feat/<PARENT>
   ```
   Then, for each open sub-branch, rebase and (after confirming) force-push:
   ```bash
   git switch feat/<SUB>
   git rebase --onto feat/<PARENT> "$OLD_PARENT"
   git push --force-with-lease origin feat/<SUB>
   ```
5. Once every sub-issue PR is squashed into the parent branch, open the parent PR against the default branch, titled with the parent's id, and list each sub-issue PR in its description. Squash-merge it after the user says to merge.

**Stacked-branch gotchas:**
- Parallel sub-branches that each inject the same dependency into one service merge cleanly but break `tsc`. After each merge, rebase the remaining sub-branches and run `tsc` before merging the next.
- Retarget dependent PRs before deleting their base branch; deleting the base closes them:
  ```bash
  gh pr edit <n> --base <new-base>
  ```
- To reopen a closed PR whose branch was force-pushed: push the branch back to its SHA at close, reopen the PR, then push the new SHA.
