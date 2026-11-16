---
name: release-notify
description: Draft Slack status updates (branch cut-off, deployment in progress, deployment complete) for a Jeeves release as Slack drafts the release captain sends, using a Notion release page as the source of truth for the service list. Trigger when a release captain wants to draft or post a release-status Slack message, or points at a Notion release page under Engineering > Releases.
---

# Jeeves Release Notify

| Slack target | Resolve with | Used for |
|---|---|---|
| Release captain's DM | `slack_read_user_profile` with no `user_id` — returns the current user's ID | Holding a preview draft the release captain sends to themself to check the rendered look |
| `#deployments` | `$JEEVES_RELEASE_CHANNEL_ID` when set, else `C03E2MRJ8JG` (`#deployments`); read the channel's name from its ID with `slack_read_channel` before naming it to the user | Default channel for the real release-update drafts |

Draft Slack updates for the three release-process milestones a Jeeves release
captain announces: branch cut-off complete, deployment in progress, and
deployment complete. Show every draft in chat for review, then save it as a
Slack draft with `slack_send_message_draft`; the release captain sends it
from **Drafts & Sent** in Slack.

## Gather the release page

Ask for (or use, if already given in the conversation) the Notion release
page URL for this release — these pages live under Engineering > Releases >
`<Year> Releases` > `<Quarter>` > `<Month> Releases`, named like
"29-Jul-2026 - Release" for a normal weekly release or
"07-Oct-2026 - Hotfix Release (accounting)" for a hotfix (`DD-Mon-YYYY`). Fetch it with
`notion-fetch`.

Pull three things from the page:

- The release date, from the page title.
- Whether this is a hotfix — the page title matches `hot[- ]?fix`, case
  insensitive ("Hotfix Release", "Hot-fix Release", "Hot fix Release"),
  instead of plain "Release". This changes the header (see below).
- The "Changed Repository" column of the Tickets table — this becomes the
  service list in every message.

## Ask which stage

Ask which stage(s) to draft with `AskUserQuestion` — branch cut-off
complete, deployment in progress, or deployment complete — treating this as
the release captain's call to make explicitly, even when the request seems
to imply one (e.g. "post the release update"). Ask this as soon as the
release page is fetched (or before, if no page has been shared yet), before
drafting anything.

The one exception: the `hotfix-captain` agent drafts all three stages by
default and lists that default in its preview for the user to confirm.

## Normalize the service list

Repository names in the Tickets table are typed by hand, so the same service
commonly shows up under several spellings across rows: with or without the
`-service` suffix (`billpay` / `billpay-service`), as a casual shorthand
(`web` for `jeeves-web`, `flows` for `flows (jumanji)`), with inconsistent
casing (`Wallet` / `wallet-service`), or as several values stacked in one
cell (multi-line) when a ticket touches more than one repo.

Work through the column with this in mind:

1. Split multi-line cells into individual values, then dedupe.
2. Match each value to a canonical Jeeves repo name — treat differing case,
   backticks, and presence/absence of `-service` as the same service.
3. When a value is a shorthand or abbreviation you can't confidently expand
   on your own (e.g. `pts`, `exp-man`), use context from the same row — the
   POD name and the other repos listed alongside it — to form a best guess,
   then show that reasoning and your guess to the user and ask them to
   confirm before it goes in the message. Confirm each guessed name with the
   user.
4. Once every value is resolved, present the final deduped list back to the
   user alongside the draft message(s) so they can catch anything before it
   ships.

## Draft the message(s)

Use this template for every stage. Draft exactly the stage(s) the release captain asked for, even
when the release clearly has other stages too.

@here
<🚩 / 🚑> *<RELEASE / HOT-FIX> — <release-date>*

📌 Stage:  <Branch Cut-off ✂️ / Deployment 🚀>
<🟢 / 🟡> Status: <COMPLETE ✅ / IN PROGRESS ⏳>
🏢 Environment: <Pre-Prod 🧪 / Production 🌐>

🛠️ *Services:*
• `<one bullet per normalized service, in inline code formatting>`

🔗 *Release page:* <bare Notion URL, no angle brackets or pipe syntax>

Every message opens with a channel-wide mention on its own line, then the
header, using the header text for this release's type (weekly vs hotfix, from
the page title check above).

| Release type | Header text |
|---|---|
| Weekly release | `🚩 *RELEASE — <release-date>*` |
| Hotfix | `🚑 *HOT-FIX — <release-date>*` |

The hotfix header drops the word "RELEASE" entirely, since "HOT-FIX" already
implies it.

A draft reaches Slack by one of two paths, each with its own mention form:

| Path | Mention on the first line |
|---|---|
| Saved with `slack_send_message_draft` | `<!here>` — the API pings only on this form |
| Pasted from chat into Slack's compose box | `@here` |

Show the draft in chat as bare, unfenced plain text with `@here`, so a
straight copy-paste renders the `*bold*` headers, the `` `inline code` ``
service names, and the link as Slack shows them; a fence copied along with the
content turns the whole message into one literal code block.

Per-stage values (the header itself doesn't vary by stage — see the release-
type table above):

| Stage | Stage field value | Status icon + text | Environment |
|---|---|---|---|
| Branch cut-off complete | Branch Cut-off ✂️ | 🟢 COMPLETE ✅ | Pre-Prod 🧪 |
| Deployment in progress | Deployment 🚀 | 🟡 IN PROGRESS ⏳ | Production 🌐 |
| Deployment complete | Deployment 🚀 | 🟢 COMPLETE ✅ | Production 🌐 |

## Keep the service list plain, keep the Slack-native layout

Slack is the destination, so only part of the shared reporting vocabulary in
`../../references/output-style.md` (plugin root) transfers:

- **Name the service and nothing else.** Each bullet holds the service name in
  inline code: `• \`wallet-service\``. The Status line at the top of the
  message already states where the release stands, and it applies to every
  service in the list — so the shared doc's per-service status icons stay
  behind here.
- **Keep one line per service.** Slack renders no markdown tables, so the
  shared doc's "rows go in a table" rule stays behind too — keep this layout
  as it is rather than converting the service list to a table.
- **Keep the in-chat preview clear**: the same bare, unfenced plain text the
  release captain will paste.

## Show the draft, then preview in Slack before the real channel

Show the drafted message(s) in chat exactly as they'd appear in Slack, along
with the normalized service list and any shorthand you had to guess at (see
above), so the release captain can catch problems before anything is sent.

Once the release captain says a draft is final, ask with `AskUserQuestion`:
"Want a preview draft in your DM first, or the draft straight in
#deployments?" — swap in the target channel's real name, read from its ID
(default `#deployments`, see the table at the top), so the question names the
channel the message will land in; other release captains use different channels, and even this user may
want a different one for a particular release.

For a DM preview, take the final chat text, swap the first line to `<!here>`,
keep the rest identical, and save it with `slack_send_message_draft` in the
release captain's own DM (see the table at the top). The captain sends it to
themself to check the real rendered look and feel — emoji, bold, inline code,
and the link. Once they confirm it's good to go, save that same `<!here>` text
as a draft in the real channel as its own separate `slack_send_message_draft`
step.

For a direct draft, swap the first line to `<!here>` the same way and save it
with `slack_send_message_draft` straight in the confirmed channel.

Slack holds one draft per channel. When the tool returns
`attached_draft_exists`, ask the release captain to send or delete the
existing draft in that channel, then save the new one.

## Reporting results

After each saved draft, report three things:

- The channel the draft landed in, by name.
- That the draft is saved, with the stage it covers.
- Where to send it from: **Drafts & Sent** in Slack.

Leave out the API calls made, a second copy of the message text, and closing
offers.
