# Reviewing the PR

Step 5 of the loop in `SKILL.md`, and the one review checklist: the
coordinator and the `jeeves:jaidev-pr-reviewer` agent both review against
"Review checklist" below.

## Steps

When Jaidev opens the PR:

1. Read `.github/CODEOWNERS` when the file exists and tell the user any approval the merge needs besides theirs.
2. Wait until every check has completed, SonarCloud included. Jaidev pushes
   fixes for bot findings on its own, so review the head that remains after
   that fix.
3. Review the PR against "Review checklist", in a fresh
   `jeeves:jaidev-pr-reviewer` agent when background agents run the batch:
   the ticket agent reports the settled head, the reviewer writes the draft
   to the scratchpad, and the ticket agent posts it after the user approves.
   `references/background-agents.md` ("Starting a PR reviewer") holds the
   spawn prompt.
4. Trace each finding through the code path and its call sites. Report
   verified findings as issues and the rest as questions.
5. Give the user a verdict, the issues, and draft specific, actionable
   GitHub review comments, all in one review. Show the user the review, then
   wait for the user's yes, and post it — Jaidev picks up PR review comments
   as a revision.
6. When nothing needs changing, confirm the head still matches the SHA you
   reviewed, and propose an Approve review. Show the user the proposal, then
   wait for the user's yes, and submit it. The approval goes out under the
   user's account.
7. Read the merge box and tell the user any requirement still missing, such
   as another required reviewer.
8. Draft follow-ups that belong outside the PR as new tickets for the user,
   each blocked by this ticket.

## Review checklist

Review against the head SHA you record:

- the old behaviour against the new, path by path;
- the diff against the briefing's Changes, Constraints and Acceptance
  criteria, using the PR's own file list (the result comment counts only
  the last session's files);
- the diff against the design doc: names, signatures and behaviour;
- the title follows the ticket format (e.g. `feat: [WAL-123] - …`);
- CI results, noting which failures are known and expected;
- every SonarCloud finding on the head;
- tests and coverage;
- logging: every `logger.*` call;
- generated files regenerate with no diff, and the lockfile adds or
  removes only what the change needs;
- the effect beyond the PR: the deploy build (e.g. the Dockerfile's
  `npm run build`) and other open PRs against the same base;
- the diff is clean of secrets and internal hostnames;
- each finding traced through its call sites before it is reported.

## Commands

Read the head SHA, review state and checks:

```bash
gh pr view <number> --json headRefOid,reviewDecision,mergeStateStatus,statusCheckRollup --jq '{head: .headRefOid, merge: .mergeStateStatus, review: .reviewDecision, checks: [.statusCheckRollup[] | {n: (.name // .context), s: .status, c: (.conclusion // .state)}]}'
```

Submit the approval:

```bash
gh pr review <number> --approve
```

## Revision rounds

Jaidev gets 3 attempts per PR, and each review round uses one — a SonarCloud
finding counts as a round. When the third still falls short, stop and hand
the ticket to the user.
