---
name: release-captain
description: Draft and post Slack status updates (branch cut-off, deployment in progress, deployment complete) for a Jeeves release, using a Notion release page as the source of truth for the service list. Trigger when a release captain wants to draft or post a release-status Slack message, or points at a Notion release page under Engineering > Releases.
---

# Release Captain

| Slack target | ID | Used for |
|---|---|---|
| `#release-channel` | `C03E2MRJ8JG` | Default posting target for the real release updates — same channel org-wide |

Before posting to the real channel, this skill sends the release captain a
private preview of the finalized draft in their own Slack DM (see "Show the
draft, then preview in Slack" below). Resolve that DM target fresh each time
from the connected Slack account's own `user_id` — the Slack tools report it
in their descriptions as the current logged-in user's `user_id`.

Draft Slack updates for the release-process milestones a Jeeves release
captain announces:

| Milestone |
|---|
| Branch cut-off complete |
| Deployment in progress |
| Deployment complete |

Always show every draft in chat for review before posting — sending a
message to Slack needs the release captain's explicit go-ahead each time,
the same as any other send-on-someone's-behalf action.

## Gather the release page

Ask for (or use, if already given in the conversation) the Notion release
page URL for this release — these pages live under Engineering > Releases >
`<Year> Releases` > `<Quarter>` > `<Month> Releases`, named like
"29-July-2026 - Release". Fetch it with `notion-fetch`.

Pull two things from the page:

- The release date, from the page title.
- The "Changed Repository" column of the Tickets table — this becomes the
  service list in every message.

## Normalize the service list

Repository names in the Tickets table are typed by hand, so the same service
commonly shows up under several spellings across rows:

| Variation | Example |
|---|---|
| With/without the `-service` suffix | `billpay` / `billpay-service` |
| Casual shorthand | `web` for `jeeves-web`; `flows` for `flows (jumanji)` |
| Inconsistent casing | `Wallet` / `wallet-service` |
| Multiple values stacked in one cell (multi-line) | a ticket that touches more than one repo |

Work through the column with this in mind:

1. Split multi-line cells into individual values, then dedupe.
2. Match each value to a canonical Jeeves repo name — treat differing case,
   backticks, and presence/absence of `-service` as the same service.
3. For a shorthand or abbreviation you can't confidently expand (e.g. `pts`,
   `exp-man`), use context from the same row — the POD name and the other
   repos listed alongside it — to form a best guess. Show that reasoning and
   your guess to the release captain, and get their confirmation before it
   goes in the message: the service list is the message's main content, so
   confirmation is what keeps it accurate.
4. Once every value is resolved, present the final deduped list back to the
   user alongside the draft message(s) so they can catch anything before it
   ships.

## Draft the message(s)

Use this template for every stage. Draft exactly the stage(s) the release captain asked for, even
when the release clearly has other stages too.

🚩 *RELEASE — <release-date>*

📌 Stage:  <Branch Cut-off ✂️ / Deployment 🚀>
<🟢 / 🟡> Status: <COMPLETE ✅ / IN PROGRESS ⏳>
🏢 Environment: <Pre-Prod 🧪 / Production 🌐>

🛠️ *Services:*
• `<one bullet per normalized service, in inline code formatting>`

🔗 *Release page:* <bare Notion URL, no angle brackets or pipe syntax>

Show this draft in chat as plain text, with no surrounding code fence, so a
straight copy-paste into Slack's compose box renders the `*bold*` headers,
the `` `inline code` `` service names, and the link as intended.

Per-stage values:

| Stage | Header emoji | Stage field value | Status icon + text | Environment |
|---|---|---|---|---|
| Branch cut-off complete | 🚩 | Branch Cut-off ✂️ | 🟢 COMPLETE ✅ | Pre-Prod 🧪 |
| Deployment in progress | 🚀 | Deployment 🚀 | 🟡 IN PROGRESS ⏳ | Production 🌐 |
| Deployment complete | 🎉 | Deployment 🚀 | 🟢 COMPLETE ✅ | Production 🌐 |

## Show the draft, then preview in Slack before the real channel

Show the drafted message(s) in chat exactly as they'd appear in Slack, along
with the normalized service list and any shorthand you had to guess at (see
above), so the release captain can catch problems before anything is sent.

Once the release captain calls a draft final, send that exact text with
`slack_send_message` to their own Slack DM (resolve their user ID from the
connected Slack account, as noted above) so they can check the rendered look
and feel — emoji, bold, inline code, and the link — before it goes anywhere
public. Send it as soon as they call the draft final; this preview goes to
the release captain themselves, so it proceeds without a separate ask.

After the preview lands, ask whether it's good to go or needs another pass.

Before posting to the real channel, name the target channel out loud and
confirm it. Default to `#release-channel` (see the table at the top), and
let them redirect to a different channel for a particular release.

Post with `slack_send_message` as its own separate step, after the user has
reviewed the text and said to go ahead.

Use a bare URL for the release-page link. It renders as a link both when
posted through the Slack API and when the draft is copy-pasted into Slack's
compose box.
