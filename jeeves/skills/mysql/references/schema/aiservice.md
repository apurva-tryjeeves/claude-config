# jeeves-ai schema notes

Database names per env: the service table in `SKILL.md` ("Default").

## `gl_code_mapping_requests`

One row per GL code agent run (`POST /accounting/agents/gl-code`): which company asked, which model ran, how it ended and the tokens it used.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | char(36) | PK |
| `request_id` | varchar(255), unique | id sent by accounting-service (a UUID), or `glc_<hex>` when jeeves-ai generates it |
| `company_id` | int, nullable | Jeeves company id |
| `status` | enum | `PENDING`, `PROCESSING`, `SUCCESS`, `FAILED` |
| `model_type` | varchar(50) | e.g. `models/gemini-3-flash-preview` |
| `items_count` | int | transactions in the request |
| `token_usage_metadata` | json | token counts per model, batches processed |
| `error_message` | text | set on `FAILED` |
| `created_at`, `completed_at` | datetime | |

## `gl_code_request_items`

One row per transaction sent in a run: the agent's input for that transaction.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | char(36) | PK |
| `mapping_request_id` | char(36) | FK → `gl_code_mapping_requests.id` |
| `item_id` | varchar(255) | accounting-service transaction id |
| `name` | varchar(500) | merchant or vendor name; `Unknown` when the transaction has none |
| `type` | enum | `CARD`, `BILLPAY` |
| `item_metadata` | json | amount, currency, merchant or vendor, additional_context (memo, note, description, payment_purpose) |

## `gl_code_item_mappings`

The agent's output for each transaction: one row per mapping type.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | char(36) | PK |
| `request_item_id` | char(36) | FK → `gl_code_request_items.id` |
| `mapping_type` | varchar(50) | `GL_CODE`, `SUPPLIER` |
| `selected` | varchar(255) | chosen GL code or supplier id; NULL with `NO_MATCH` |
| `match_type` | varchar(50) | `EXACT_MATCH`, `FUZZY_MATCH`, `ALIAS_MATCH`, `SUBSIDIARY_MATCH`, `HISTORICAL_MATCH`, `CATEGORY_INFERRED`, `WEB_SEARCH_INFERRED`, `PATTERN_MATCH`, `WEAK_GUESS`, `NO_MATCH` |
| `confidence` | float | fixed per match_type, 1.0 down to 0 |
| `reasoning` | text | the model's 1–2 sentence explanation |

Join keys: `gl_code_request_items.mapping_request_id` → `gl_code_mapping_requests.id`; `gl_code_item_mappings.request_item_id` → `gl_code_request_items.id`

The rendered prompt, the raw model response, the supplier and GL code option lists and the company's existing mappings live only in memory during the run; these three tables hold the transaction inputs and the parsed outputs.

```sql
SELECT r.request_id, r.company_id, r.created_at, i.item_id, i.type, i.name,
       i.item_metadata, m.mapping_type, m.selected, m.match_type, m.confidence, m.reasoning
FROM gl_code_mapping_requests r
JOIN gl_code_request_items i ON i.mapping_request_id = r.id
JOIN gl_code_item_mappings m ON m.request_item_id = i.id
WHERE r.company_id = <company_id>
ORDER BY r.created_at DESC
LIMIT 100
```
