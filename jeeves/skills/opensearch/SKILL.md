---
name: opensearch
description: Search JeevesInc application logs on the OpenSearch clusters, and manage alerting monitors over the Alerting API. Trigger when the user asks to search or debug production logs, find the log lines for a batch, sync or trace id (a transaction UUID goes to trace-tx), or create, update or list an OpenSearch monitor or notification channel.
---

# OpenSearch — application logs and alerting monitors

| Environment | MCP server | AWS profile | Region |
| --- | --- | --- | --- |
| prod | `opensearch-prod` | `jeeves_prod` | `us-east-1` |
| dev | `opensearch-dev` | `jeeves_dev` | `us-east-2` |

Every profile shares one `sso-session`; log in as `jeeves:aws-secrets` "Authentication" describes.

| Operation | Reach it with | Depth |
| --- | --- | --- |
| Search logs | the `opensearch-*` MCP tools | this file |
| Manage alerting monitors | `awscurl --service es` | `references/alerting-api.md` |

## Search logs

All Jeeves services ship app logs into **daily indices `logs-YYYY.MM.DD`**
(e.g. `logs-2026.06.30`).

### Key fields

- `@timestamp` — for a date-range filter.
- `app_name` / `app_name.keyword` — the emitting pod's `app` label, taken from each service's deployment names in `jenkins-library` `vars/jeevesPlatformInfo.groovy`. Examples: `accounting-api`, `accounting-worker`, `accounting-jobexecutor`, `wallet-api`, `wallet-worker`, `stablecoin-service`, `stablecoin-service-worker`, `stablecoin-service-cron`. Filter on `.keyword` to scope to one service.
- `log` — text field holding the full JSON log line **and** raw SQL.
- `pid` — set by the application logger, absent from OpenTelemetry SDK lines.
- `traceId` / `trace_id` and `jeeves_trace_id` — two distinct per-request correlation ids, present on request/response-cycle logs (absent on background jobs, startup logs, etc). Both persist identically across every service a single request touches — group by either to pull the whole cross-service chain for one request in a single query, no need to query service-by-service.
  - `traceId` / `trace_id` — the OTel W3C trace-context id (hex format), propagated via the standard `traceparent` header. Use this to cross-reference with APM/tracing tooling.
  - `jeeves_trace_id` — Jeeves's own application-level request id (UUID-hex format), generated independently of OTel. Use this when a caller or client-facing log references "the request trace id."

### Query patterns

**A known batch/sync UUID:** (a transaction UUID with the question "what happened to it" goes to `jeeves:trace-tx`) `match_phrase` on the `log` field, plus a `@timestamp` range filter (and an `app_name.keyword` filter to scope to a service). Service-specific breadcrumbs show up in `log` — e.g. accounting's Codat calls log as `[CodatAPI] Call for method[...]` with full request/response.

**A known request trace id:** exact `term` filter on `traceId.keyword` or `jeeves_trace_id.keyword` (whichever id you have), plus a `@timestamp` range filter. Omit the `app_name.keyword` filter to pull every service the request touched in one query:

```json
{
  "query": {
    "bool": {
      "must": [
        { "term": { "jeeves_trace_id.keyword": "96e85e90fae3d6ecf84cad28ee2b0bd9" } },
        { "range": { "@timestamp": { "gte": "2026-08-06T00:00:00Z", "lte": "2026-08-06T23:59:59Z", "format": "strict_date_optional_time||epoch_millis" } } }
      ]
    }
  },
  "sort": [{ "@timestamp": { "order": "asc" } }]
}
```

Example, via `mcp__opensearch-prod__SearchIndexTool`:

```json
{
  "index": "logs-2026.06.30",
  "query_dsl": {
    "query": {
      "bool": {
        "must": [
          { "match_phrase": { "log": "<transaction-uuid>" } },
          { "range": { "@timestamp": { "gte": "2026-06-30T00:00:00Z", "lte": "2026-06-30T23:59:59Z", "format": "strict_date_optional_time||epoch_millis" } } }
        ],
        "filter": [{ "term": { "app_name.keyword": "wallet-api" } }]
      }
    }
  }
}
```

**A log level:** phrase matching on `log` is case-insensitive, so `"level":"ERROR"` also matches the OpenTelemetry SDK's own `"level":"error"` lines. Add `{"exists": {"field": "pid"}}` to keep application logs only.

**Large result sets** get written to a file with very long lines, which the Read tool would otherwise truncate. Parse it instead with a Python heredoc slicing the JSON:

```bash
python3 - <<'PY'
import json
hits = json.load(open("<result-file>"))["hits"]["hits"]
for h in hits[:20]:
    print(h["_source"]["@timestamp"], h["_source"]["log"][:300])
PY
```

For a service's DB tables, use the `jsql` wrapper with that service's database (see the `jeeves:mysql` skill).

### Reporting results

Icons, linking and value-rendering vocabulary live in the shared
`${CLAUDE_PLUGIN_ROOT}/references/output-style.md` — follow it rather than inventing a format.

- **Lead with a verdict line** — icon, what was found, the hit count, and the
  window searched. Example: `❌ 43 hits — wallet-worker, 6 Aug 00:00–23:59`.
- **Quote only the lines that carry the meaning** in a fenced block, with the
  surrounding log left out. Prefix each with its human timestamp.
- **Group many similar hits** into a counts table keyed by what distinguishes
  them (error message, `app_name`, currency pair), with `Count` and `First seen`
  columns per the shared doc's grouping table, plus one sample line fenced below.
- **Render `@timestamp` as local time** (`6 Aug 5:56am`), and keep trace ids,
  transaction UUIDs and `app_name` values written in full.

Answer what was asked, then stop — leave out the query DSL you ran, index
inventories and "want me to search further?" follow-ups. Call out a caveat that
changes the next step: zero hits because the index for that date is absent, or a
window that hit the result-size cap so the counts are a floor.

## Manage alerting monitors

Monitors and notification channels are cluster config, held in OpenSearch rather
than in a repo. The MCP tools read logs only, so reach the Alerting API with
`awscurl --service es`, which signs each request with SigV4.

Before any create, update, delete or `_execute`, state the cluster, the monitor
(name and id) and the action, and get the user's go-ahead — these change shared
alerting and can post to Slack.

Read `references/alerting-api.md` before creating, updating, listing or deleting
a monitor, wiring a Slack channel, or deep-linking an alert into Discover. It
carries:

- the `awscurl` invocation, credential export and CA bundle each request needs
- the Alerting and Notifications endpoints, and what `_execute` does
- monitor body notes — `{{period_end}}` date math, `severity`, `throttle` units,
  alert auto-resolve, and Slack's `<url|text>` link syntax
- the route that sends a multi-line `message_template` intact
- per-account lookups to extend as you resolve them: notification channel config
  ids, and Discover index-pattern saved-object ids
- how briefly to report monitor work
