# Schema notes

One file per service (`wallet.md`, `stablecoin.md`, `develop.md`, ...), matching
the service names in the main SKILL.md database table. Shared across that
service's `_<n>` env variants, since dev/preprod/prod share the same schema.

Each file accumulates one section per documented table:

```markdown
## <table_name>

| Column | Type | Notes |
| --- | --- | --- |
| id | bigint | PK |
| status | varchar | enum values: `pending`, `active`, `closed` |
| created_at | datetime | UTC, `YYYY-MM-DD HH:MM:SS` |

Join keys: `<table>.wallet_id` → `wallets.id`
```

Append a new table section the first time it's queried; extend an existing
section when a new column/enum/join is discovered on a later query.
