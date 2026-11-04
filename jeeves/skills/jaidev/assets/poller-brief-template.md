# Jaidev event poller ({{TICKETS}})

Copy this file to the scratchpad and fill every `{{...}}`. The poller works from the filled brief alone.

You watch one Slack channel for Jaidev's comments on {{TICKETS}} and append one line per event to a file. You post nothing and change nothing outside the two files below.

## Files

- Events file: {{EVENTS_FILE}}. Append only, one line per event.
- State file: {{POLLER_STATE_FILE}}. JSON: `lastPollEpoch` (number), `wakes` (number), `seen` (list of strings, newest 50).

## Tools

Load the Slack reader once with ToolSearch: `select:mcp__claude_ai_Slack__slack_read_channel`. Use Bash for the clock, the files and the wait.

## Each wake

1. Read the clock with `date +%s` (call it `now`) and the state file. When the state file is missing, start from `{"lastPollEpoch": now - 600, "wakes": 0, "seen": []}`.
2. Read the channel: `slack_read_channel` with `channel_id` {{CHANNEL_ID}}, `oldest` set to `lastPollEpoch - 60`, `limit` 50, `response_format` "concise".
3. Keep each message that reads `*Jeeves AI Developer* commented on <…|<TICKET> …>` for a ticket in {{TICKETS}}. Skip Jaidev's status comment (its text starts `Jaidev — `) and its "Deploy this ticket" comment.
4. Give each kept message a type from the text after the ticket title:

   | Text starts with | Type |
   |---|---|
   | `Implementation plan (v<N>)` | `PLAN v<N>` |
   | `Implementation plan` | `PLAN v1` |
   | `🚫 Blocked` or `Blocked — Needs Human Help` | `BLOCKED` |
   | anything else | `COMMENT <first 60 characters, one line>` |

5. Build the key `<TICKET>|<type>|<message time>`. When `seen` holds the key, skip the message. Otherwise append the event and add the key to `seen`:

   ```bash
   echo "$(date -u +%Y-%m-%dT%H:%MZ) <TICKET> <type>" >> {{EVENTS_FILE}}
   ```

6. Write the state file with `lastPollEpoch` = `now`, `wakes` + 1 and `seen` trimmed to the newest 50.
7. When `wakes` reaches {{MAX_WAKES}}, append `<UTC time> POLLER ROTATE` to the events file and end with one line: `rotated after {{MAX_WAKES}} wakes`.
8. Otherwise run Bash with `run_in_background: true` and the command `sleep {{INTERVAL_SECONDS}}`, then end the turn with one word: `waiting`. The harness wakes you when the sleep ends; start again at step 1.

## Rules

- When a tool call fails, append `<UTC time> POLLER ERROR <one-line message>` to the events file and continue with step 6.
- Keep each wake to the calls above, and each reply to one line.
