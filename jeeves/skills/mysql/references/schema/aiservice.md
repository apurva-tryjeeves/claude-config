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

## `accounting_settings_sessions`

One row per bulk-import upload to the accounting settings agent (GL codes, tax rates, suppliers, custom-field values). Answers "what happened to this upload, and was it tied to a custom field".

| Column | Type | Notes |
| --- | --- | --- |
| `id` | char(36) PK | |
| `session_id` | varchar(36), unique | the id the UI and logs use; `accounting_settings_items.session_id` joins here |
| `company_id` / `user_id` | int | |
| `phase` | varchar(40) | seen: `analyzing`, `reviewing` |
| `file_name` / `file_s3_key` | varchar | |
| `category_id` | varchar(36), nullable | `company_accounting_categories.id` (accounting DB) when uploaded from a custom field's Import; `NULL` from the general Import. Non-null means the ACC-1692 upload-target prompt rule ran |
| `items_total` / `items_new` / `items_existing` | int | filled when analysis ends |
| `classification` / `apply_results` | json | |
| `created_at` / `updated_at` / `deleted_at` | datetime | UTC |

## `accounting_settings_items`

One row per extracted item in a session.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | char(36) PK | |
| `session_id` | varchar(36) | FK `accounting_settings_sessions.session_id` |
| `setting_type` | varchar(40) | seen: `gl_code`, `category` (custom-field value) |
| `status` / `match_status` / `action` | varchar(40) | |
| `data` / `raw_data` / `api_result` | json | |
| `existing_id` | varchar(64) | |

Item count per type for a company's uploads:

```sql
SELECT s.session_id, s.category_id, i.setting_type, COUNT(*) AS n
FROM accounting_settings_items i
JOIN accounting_settings_sessions s ON s.session_id = i.session_id
WHERE s.company_id = <companyId>
GROUP BY s.session_id, s.category_id, i.setting_type
```
