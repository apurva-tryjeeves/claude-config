# Reusable queries

Shared across the `jeeves:prod-debug`, `jeeves:post-deploy-verify`,
`jeeves:feature-plan` and `jeeves:trace-tx` skills. The user grows this over time. When they share a SQL query or an OpenSearch search string, append it to the copy in your clone of the plugin (`${JEEVES_PLUGIN_SRC:-$HOME/github/apurva-tryjeeves/claude-config}/jeeves/references/queries.md`), left uncommitted for the user to review and push — or report it when the clone is missing, under the right section with a one-line "when to use" note. Keep entries copy-pasteable.

## SQL — production (`jsql prod/<database> '<sql>'`, read-only)
<!-- e.g.
### Wallet transaction by id
```bash
jsql prod/wallet '
SELECT id, transactionStatus, transactionAmount, transactionCurrency, createdAt
FROM wallet_transactions
WHERE id = "<id>"
'
```
-->
_(none yet — add as shared)_

## SQL — dev/preprod (`jsql dev-NN/<service> '<sql>'`, `jsql preprod/preprod_<service> '<sql>'`)
_(none yet — add as shared)_

## OpenSearch — prod (`mcp__opensearch-prod__*`, indices `logs-YYYY.MM.DD`)
<!-- e.g.
### Trace a request across services
match_phrase on `log` = "<jeeves-trace-id>", filter @timestamp range, optionally app_name.keyword = "wallet-api"
-->
_(none yet — add as shared)_

## OpenSearch — dev (`mcp__opensearch-dev__*`)
_(none yet — add as shared)_

## Notes / gotchas the user has shared
_(none yet)_
