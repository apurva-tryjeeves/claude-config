# OpenSearch Alerting API — monitors and notification channels

| Environment | Endpoint | AWS profile | Region |
| --- | --- | --- | --- |
| prod | `https://opensearch.prod.jeeves.vpn` | `jeeves_prod` | `us-east-1` |
| dev | `https://opensearch.dev.tryjeeves.vpn` | `jeeves_dev` | `us-east-2` |

Both domains authenticate with AWS SigV4 and serve a certificate issued by the
private `CN=tryjeeves` CA.

## Send requests with awscurl

Set the CA bundle, load the SSO session into environment variables, then call
`awscurl --service es`:

```bash
# pick the row you need from the environment table above
ENDPOINT="https://opensearch.prod.jeeves.vpn"
PROFILE="jeeves_prod"
REGION="us-east-1"

export SSL_CERT_FILE="$HOME/zscaler-merged-ca-bundle.pem"
export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
eval "$(aws configure export-credentials --profile "$PROFILE" --format env)"

uvx awscurl --service es --region "$REGION" \
  -X GET "$ENDPOINT/_plugins/_alerting/monitors/<monitor_id>"
```

- Supply the SSO session with `aws configure export-credentials` — `awscurl`
  reads credentials from environment variables.
- Point both CA variables at `~/zscaler-merged-ca-bundle.pem`, which carries the
  `tryjeeves` root CA (build it per the marketplace README). A run against the stock trust store or
  `~/zscaler-root-ca.pem` reports `unable to get local issuer certificate`.
- Sign every request with `awscurl --service es`; the domain answers an unsigned
  `curl` with `HTTP 401`.

## Send a monitor body from a file

Shell variables are lost between Bash calls, so run the setup block above and
this request in one Bash call. Pass the JSON through `-d "$(cat file)"` so
escape sequences arrive verbatim:

```bash
uvx awscurl --service es --region "$REGION" \
  -X PUT "$ENDPOINT/_plugins/_alerting/monitors/<monitor_id>" \
  -H 'Content-Type: application/json' -d "$(cat monitor.json)"
```

Use this route for any monitor whose `message_template.source` holds newlines: the Dashboards Dev Tools console rejects them (`Illegal unquoted character ((CTRL-CHAR, code 10))`), and it reads a blank line as a request separator, so keep the `{` directly under the request line.

## Endpoints

| Action | Request |
| --- | --- |
| Create | `POST _plugins/_alerting/monitors` |
| Update | `PUT _plugins/_alerting/monitors/<monitor_id>` |
| Read | `GET _plugins/_alerting/monitors/<monitor_id>` |
| List | `GET _plugins/_alerting/monitors/_search` |
| Delete | `DELETE _plugins/_alerting/monitors/<monitor_id>` |
| Run now (dry run) | `POST _plugins/_alerting/monitors/<monitor_id>/_execute?dryrun=true` |
| Channels | `GET _plugins/_notifications/configs` |

Pass `?dryrun=true` to `_execute` — it then runs the query and evaluates the
trigger while creating no alert and sending no notification. A bare `_execute`
defaults to `dryrun=false`: it creates alerts and fires the monitor's actions,
including Slack messages. Confirm before any POST, PUT, DELETE or `_execute` as `SKILL.md` "Manage alerting monitors" says.

Create and update return `_id` and `_version`. Read the monitor back to confirm
what was stored: `track_total_hits: true` returns as `2147483647`, and
`gte`/`lte` return as `from`/`to` with `include_lower`/`include_upper`.

## Monitor body notes

- `{{period_start}}` / `{{period_end}}` are substituted per run and stored
  verbatim as strings at create time. Date math applies to them:
  `"gte": "{{period_end}}||-7m"` with `"format": "epoch_millis"`.
- `severity` is a `"1"`–`"5"` string that sorts and filters the Alerts
  dashboard. Delivery comes from the action's channel.
- `throttle.unit` takes `MINUTES`, so 24 hours is
  `{"value": 1440, "unit": "MINUTES"}`.
- Query-level alerts return to `COMPLETED` on their own once the condition stops
  matching.
- Slack renders `subject_template` as the first line and `message_template` as
  the body. Wrap URLs as `<url|link text>` so Slack links text whose URL holds
  parentheses and quotes.

## Notification channels

A channel's config id is the last path segment of its channel-details URL:

```
.../app/notifications-dashboards#/channel-details/JUIK640BAvEjoJNCY-mL
```

| Channel | Config id |
| --- | --- |
| `slack-cat-ops` | `JUIK640BAvEjoJNCY-mL` |

Put the config id in the action's `destination_id`. When you wire a channel this
table does not list, record its row in this file, following `references/write-back.md` at the plugin root.

## Deep-link an alert into Discover

Discover addresses index patterns by saved-object id, so the URL carries the id
rather than the pattern name. Read ids from `.kibana` with a `term` filter on
`type: index-pattern`, and record each further pattern you resolve here:

| Index pattern | Saved-object id |
| --- | --- |
| `logs-*` | `81fb7c60-effd-11ed-bf4e-4d15d6b855b8` (the cluster's `defaultIndex`) |

```
<endpoint>/_dashboards/app/data-explorer/discover#?_a=(discover:(columns:!(app_name,msg),isDirty:!f,sort:!()),metadata:(indexPattern:'<index_pattern_id>',view:discover))&_g=(filters:!(),refreshInterval:(pause:!t,value:0),time:(from:'{{ctx.periodStart}}',to:'{{ctx.periodEnd}}'))&_q=(filters:!(),query:(language:kuery,query:'<kql>'))
```

Encode spaces in the KQL as `%20` and keep the rison string single-quoted.

## Report monitor work

Give the monitor name, its id and the outcome — one row per monitor when several
changed. Leave out the payload sent and the verification calls made. Call out a
monitor that reads back `enabled: false`, a create that returned no `_id`, or a
`_search` that capped at its page size while the cluster holds more monitors.
