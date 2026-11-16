# Reviewing the plan

Step 4 of the loop in `SKILL.md`: compare Jaidev's latest "Implementation
plan" with the ticket, the briefing and the design doc, and send one
correction or the approval.

## Expected gaps in plan v1

Plan v1 usually needs one correction round. Expect these gaps and check each
first:

- the Affected Services table shows the base as `development`, the default
  branch, instead of the briefed one (ACC-1669, ACC-1670);
- names are invented where the briefing's names arrived blank;
- Done-when is short of the full criteria list (4 of 8 on ACC-1669);
- acceptance criteria arrive blank;
- code is written as prose instead of in full (a class on ACC-1669).

## Checklist

Compare Jaidev's latest "Implementation plan" with the ticket, the
briefing and the design doc, item by item:

- repository and base branch match;
- the quote-back matches the briefing;
- the Implementation Sequence writes out every code block from the names
  comment and the plan feedback in full, exactly as briefed;
- every Change and Acceptance criterion is covered, value by value — rule
  names, options, versions and file names exactly as briefed. An item is
  covered when the plan names its value; a preset that "includes most of
  it" counts as missing;
- scope matches the ticket, and the files belong to this ticket alone;
- names, signatures and behaviour match the design doc; report each
  difference as a decision for the user;
- each Key Assumption holds — verify it in the code. A revised plan may omit
  the section; verify the assumptions it now relies on;
- risks and mitigations are acceptable.

## Correction

Send the correction as one feedback reply that holds, in plain fenced
blocks:

- the base branch, restated;
- the Names table, and the rest of the names comment again when plan v1
  still misses names or code;
- every code block over ~20 lines held back from the names comment;
- every Done-when criterion, word for word;
- the PR title.

Approve v2 when it matches.

## Report and post

Report a verdict (approve / request changes), a table of ticket and
design-doc items → covered / missing / wrong, and any wrong assumptions. When
changes are needed, draft the feedback reply. Show the user the reply or the
approval, then wait for the user's yes, and post `@jaidev plan:approved` or
the feedback as a reply in the thread of the **latest** plan. A revised plan
arrives as a new top-level comment ("Implementation plan (v2)"), and Jaidev
resolves the previous plan's thread.
