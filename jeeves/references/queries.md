# Reusable queries

Shared across the `prod-debug`, `post-deploy-verify`, `feature-plan` and
`trace-tx` skills. The user grows this over time. When they share a SQL query or an OpenSearch search string, append it under the right section with a one-line "when to use" note. Keep entries copy-pasteable.

## SQL — production (`jsql prod/<database> "<sql>"`, read-only)
<!-- e.g.
### Wallet transaction by id
jsql prod/wallet "SELECT id, status, amount, currency, created_at FROM wallet_transactions WHERE id='<id>';"
-->
_(none yet — add as shared)_

## SQL — dev/preprod (`jsql dev-NN/<database> "<sql>"`)
_(none yet — add as shared)_

## OpenSearch — prod (`mcp__opensearch-prod__*`, indices `logs-YYYY.MM.DD`)
<!-- e.g.
### Trace a request across services
match_phrase on `log` = "<jeeves-trace-id>", filter @timestamp range, optionally app_name.keyword = "wallet-service-api"
-->
_(none yet — add as shared)_

## OpenSearch — dev (`mcp__opensearch-dev__*`)
_(none yet — add as shared)_

## Notes / gotchas the user has shared
_(none yet)_
