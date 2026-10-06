# Schema notes

One file per service, named after its dev database prefix — the `<service>` in
`jsql dev-NN/<service>` (`wallet.md`, `product_account.md`, `stablecoin.md`,
`develop.md` for the backend). One file covers that service's dev, preprod and
prod databases, which share the same schema. Write new notes in your clone of
the plugin, as the mysql skill describes.

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
