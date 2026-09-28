# Cross-service links

Logical relationships between tables in different service databases, held at
the application layer rather than a DB foreign key, since the tables live in
separate schemas.

Every service DB in a given env shares one MySQL host (confirmed: `develop-20`,
`preprod`, `prod` each resolve to a single host across all their service DBs),
so a cross-service query can be written as a single same-host, cross-schema
`JOIN`:

```sql
SELECT ...
FROM wallet_20.wallet_instrument_top_ups w
JOIN stablecoin_20.stablecoin_deposits s ON ...
```

Populate this file incrementally: append a section the first time a
cross-service query is worked out. Format:

```markdown
## <short name for the relationship>

- <service>.<table>.<column>  ↔  <service>.<table>.<column>
- Match on: <the actual join condition — e.g. a shared reference ID, not an
  enforced FK>
- Direction / lag: <which side is written first, whether there's async delay,
  whether the relationship is 1:1 or 1:many>
- Query pattern: <the cross-schema JOIN, or note if this env's services are on
  separate hosts and it needs two `jsql` calls instead>
```
