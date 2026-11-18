# Draft a reply — match the audience

Every `@jaidev` comment follows the `jaidev` skill (its comment format and
per-comment approval); this section covers all other replies.

A reply's tone and content depend entirely on who reads it. Ask which
audience if it isn't obvious from context, then draft accordingly:

| Audience | Tone | Include | Avoid |
|---|---|---|---|
| Engineering | Technical, direct | Root cause, file:line references, stack traces/error messages, ticket/PR ids | Padding, business framing |
| Product manager | Plain business language | User/business impact, current status, ETA or next milestone | Code-level detail, stack traces, internal service names |
| Customer support | Plain, non-technical | Current status in terms a customer-facing rep can relay, workaround if one exists, expected resolution timeframe | Internal architecture, ticket ids, jargon, root-cause detail they can't act on |

Write any section labels in the reply (`What's happening`, `Current status`,
`Question for product`, etc.) as markdown headers (`## Current status`) —
same reasoning as ticket descriptions in `SKILL.md` → Formatting that reads well in Linear: a real header stands out, while
bold text renders at the same size as body text and blends in.

Show every comment, a reply or a standalone addition to a ticket, as raw
markdown in a ` ````markdown ` fence and wait for the user's explicit yes
before posting, even when the first request already says "post". Once
confirmed, post with
`mcp__linear__save_comment` (`issueId` for a new thread, `parentId` to reply
within an existing one).
