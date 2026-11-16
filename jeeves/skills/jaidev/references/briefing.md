# Writing the briefing

Step 2 of the loop in `SKILL.md`: research the ticket, draft the names
comment and the start comment, and post both after the user's approval.

## Research

Research first. Jaidev plans from the ticket and its comments, so every
verified fact in the briefing becomes a correct assumption in its plan:

- Read the ticket, its related and blocking tickets, the repository, and
  every precedent PR the ticket names. Spell out every reference: when the
  ticket says "same as stablecoin-service PR 9", read that PR and write what
  it did.
- Check every factual claim in the ticket against the code — current config,
  versions, file layout, what CI runs. Brief Jaidev on what is true, and
  tell the user each correction.
- When the project has a design doc, compare the briefing and names comment
  with it section by section: names, file paths, signatures, behaviour and
  log messages. Fix clear mismatches, and bring real differences to the
  user as decisions. Briefings drift from the design doc even when they
  copy a sibling repo.
- Read how one or two sibling services do the same thing, and follow the
  setting the team already uses.
- When the ticket touches build, lint or CI, read `.github/workflows/*`, the
  inputs it passes to any reusable workflow, and the npm scripts those
  inputs run, including `pre*` hooks (e.g. `prebuild` running lint).
- Run every acceptance-criterion command in the repository before
  briefing, and adjust any that fail in Jaidev's sandbox (e.g. single
  test files need `--coverage=false` when `jest.config.js` enforces a global
  threshold). Run any code the briefing gives the same way: compile it,
  lint it under the rules it will meet (including open PRs that tighten
  them), and test it under the strictest compiler flags the team's
  guidelines require. Keep test output short: add
  `--coverageReporters=text-summary` when coverage is on, and pipe long
  runs through `tail -40`.
- Settle every identifier the briefing introduces with the
  `jeeves:typescript-naming` skill, following its "During planning" steps.
  Read the repo rules and the surrounding code first, then write the Names
  table (kind, name, file, purpose) and the renames list. The names comment
  carries the table, and Jaidev uses the names as written.

## Draft

Draft the start comment in the format in `assets/briefing-format.md`, to
these rules:

- Carry every ticket item into Changes, Acceptance criteria or Manual
  follow-up, word for word where possible.
- Put every change to `.github/workflows/*` under Manual follow-up. Jaidev's
  GitHub token pushes code only, so those changes reach the branch through
  the user (see Rules in `SKILL.md`).
- Include the Manual follow-up section only when it has items, and then add
  "A human makes the items under Manual follow-up." to the workflows
  Constraint.
- Write acceptance criteria Jaidev can meet in its sandbox: commands that
  exist in the base branch's `package.json` and single test files. Name the
  full suite and coverage gate by their CI check (`references/jaidev-reference.md` §5).
- Keep lists one level deep, with each item's detail on its own line.
- Describe credentials by name and location (e.g. the Secrets Manager key);
  keep their values out of the comment.

Split the content across the three posts in `references/jaidev-reference.md`
§5 (names comment, start comment, plan feedback):

- Draft the plan feedback's long code blocks now, with the names comment.
- Put code in plain fenced blocks and keep every section expanded, without
  `+++` collapsibles.
- Open each section of the names comment with a `## <emoji>` header, and end
  it with a line that sends questions to the replies under the
  `@jaidev start` comment.

## Post

Show the user each draft, then wait for the user's yes (see Rules in
`SKILL.md`). A general go-ahead ("coordinate with Jaidev per the skill")
starts the drafting. Then post the names comment as a **top-level comment**,
and the briefing as a second top-level comment straight after it, both under
that one approval. The plan feedback goes up after plan v1, under its own
approval.
