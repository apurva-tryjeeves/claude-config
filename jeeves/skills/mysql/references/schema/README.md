# Schema notes

One file per service, named after its dev database prefix — the `<service>` in
`jsql dev-NN/<service>` (`accounting.md`, `billpay.md`, `develop.md` for the
backend, `product_account.md`, `stablecoin.md`, `transactions.md`, `wallet.md`). One file covers
that service's dev, preprod and prod databases, which share the same schema. Write new notes following `references/write-back.md` at the plugin root.

Each file accumulates one section per documented table, in this shape — the
one template the mysql skill uses:

````markdown
## `<table>`

<one line: what the table holds and which request it answers>

| Column | Type | Notes |
| --- | --- | --- |
| `<col>` | <type> | <enum values, FK target, date format> |

Join keys: `<table>.<col>` → `<other_table>.<col>`

<the working query, fenced as sql>
````

Append a new table section the first time it's queried; extend an existing
section when a new column/enum/join is discovered on a later query.
