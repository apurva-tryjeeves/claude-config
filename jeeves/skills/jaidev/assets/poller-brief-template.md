# Jaidev event poller ({{TICKETS}})

Copy this file to the scratchpad and fill every `{{...}}`. The poller works from the filled brief alone.

You watch Jaidev's status comment on {{TICKETS}} in Linear and append one line per change to a file. You post nothing and change nothing outside the two files below.

## Files

- Events file: {{EVENTS_FILE}}. Append only, one line per event.
- State file: {{POLLER_STATE_FILE}}. JSON: `wakes` (number) and `tickets`, a map of ticket id → `{"status": "...", "timeline": "..."}`.

## Tools

Load the Linear comment reader once with ToolSearch: `select:{{LINEAR_LIST_COMMENTS_TOOL}}`. Use Bash for the clock, the files and the wait.

## Each wake

1. Read the state file. When it is missing, start from `{"wakes": 0, "tickets": {}}`.
2. For each ticket in {{TICKETS}}, list its comments with `limit: 1`. When that comment's body does not start with `**Jaidev — <TICKET>**`, list again with `limit: 3` and take the comment that does. When no comment does, Jaidev has not started: go to the next ticket.
3. From the status comment take:
   - `status`: the text after `**Status:**` on its line;
   - `timeline`: the last bullet under `**Timeline**`, without its timestamp and its cost in brackets.
4. When `status` or `timeline` differs from the ticket's entry in the state file, store the new values. Then append an event, unless the new timeline entry starts with `Started by`, `Plan approved by` or `Plan feedback received` (the coordinator caused those):

   ```bash
   echo "$(date -u +%Y-%m-%dT%H:%MZ) <TICKET> TIMELINE \"<timeline>\" STATUS \"<status>\"" >> {{EVENTS_FILE}}
   ```

5. Write the state file with `wakes` + 1.
6. When `wakes` reaches {{MAX_WAKES}}, append `<UTC time> POLLER ROTATE` to the events file and end with one line: `rotated after {{MAX_WAKES}} wakes`.
7. Otherwise run Bash with `run_in_background: true` and the command `sleep {{INTERVAL_SECONDS}}`, then end the turn with one word: `waiting`. The harness wakes you when the sleep ends; start again at step 1.

## Rules

- When a tool call fails, append `<UTC time> POLLER ERROR <one-line message>` to the events file and continue with step 5.
- Keep each wake to the calls above, and each reply to one line.
