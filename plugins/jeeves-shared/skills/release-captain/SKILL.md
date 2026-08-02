---
name: jeeves-release-notify
description: Draft and post Slack status updates (branch cut-off, deployment in progress, deployment complete) for a Jeeves release, using a Notion release page as the source of truth for the service list. Trigger when a release captain wants to draft or post a release-status Slack message, or points at a Notion release page under Engineering > Releases.
---

# Jeeves Release Notify

| Slack target | ID | Used for |
|---|---|---|
| `#release-channel` | `C03E2MRJ8JG` | Default posting target for the real release updates — same channel org-wide |

Before posting to the real channel, this skill privately sends the release
captain a preview of the finalized draft in their own Slack DM (see "Show
the draft, then preview in Slack" below). That DM target isn't a stored
ID — resolve it fresh each time from the connected Slack account's own
`user_id` (shown in the Slack tools' own descriptions as the current
logged-in user's `user_id`), and send the preview there. This works for
any release captain with no extra setup, since it's resolved from
whoever's Slack account happens to be connected.

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
3. When a value is a shorthand or abbreviation you can't confidently expand
   on your own (e.g. `pts`, `exp-man`), use context from the same row — the
   POD name and the other repos listed alongside it — to form a best guess,
   then show that reasoning and your guess to the user and ask them to
   confirm before it goes in the message. Flag these for confirmation rather
   than resolving them yourself: the service list is the main content of the
   message, so getting one wrong is the kind of mistake that's embarrassing
   once it's posted to a whole release channel.
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

Show this draft in chat as plain text, with no surrounding triple-backtick
fence. The release captain copies the draft straight out of chat and pastes
it into Slack's compose box — a fence copied along with the content makes
Slack render the whole message as one literal code block, which suppresses
the `*bold*` headers, the `` `inline code` `` service names, and the URL
link all at once. Plain text keeps a straight copy-paste faithful to how it
actually renders in Slack.

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

Once the release captain says a draft is final, send that exact text with
`slack_send_message` to their own Slack DM (resolve their user ID from the
connected Slack account, as noted above) so they can check the real
rendered look and feel — emoji, bold, inline code,
and the link — before it goes anywhere public. This preview send doesn't
need a fresh ask each time; it's a private message to the release captain
themselves, not the release channel. Send it right when they call the draft
final — that's the signal it's ready, as opposed to still mid-edit.

After the preview lands, ask whether it's good to go or needs another pass.

Before posting to the real channel, confirm the target channel. Default to
`#release-channel` (see the table at the top) since that's the release
captain's release channel, but always name it out loud and let them
redirect — other release captains use different channels, and even the same
release captain may want a different one for a particular release.

Post with `slack_send_message` as its own separate step, after the user has
reviewed the text and said to go ahead.

Use a bare URL for the release-page link, not Slack's `<url|display text>`
mrkdwn syntax. That syntax only renders as a link when a message is posted
through the Slack API — the release captain sometimes copies the draft
straight into the Slack compose box instead, where `<url|text>` shows up as
literal angle brackets around an auto-linkified raw URL. A bare URL renders
correctly either way.
