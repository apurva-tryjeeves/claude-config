# Repo → team → project map

Grows over time as tickets get created or looked up. Check this first when
resolving team/project for a repo — it skips a live `list_teams`/
`list_projects` round-trip for a repo already seen, and skips re-asking the
user something they already answered once.

One row per repo, edited per `references/write-back.md` at the plugin root. Add
a new row the first time a repo's team/project is resolved (by user
confirmation, not a guess); add a new project to an
existing repo's row when the repo starts appearing under a different active
project. Don't remove an old project when a new one appears — a repo can
have work tracked under more than one project over time; instead note which
is current.

| Repo | Team | Known project(s) |
|---|---|---|
| wallet-service | Product - Wallet (`WAL`) | Jeeves Embedded Wallet Solution (Privy) |
| sequelize-db-models | Product - Wallet (`WAL`) | _(none confirmed yet)_ |
| jeeves-simulation-server | Product - Wallet (`WAL`) | Jeeves Embedded Wallet Solution (Privy) |
| accounting-service | EPD - Accounting ERP (`ACC`) | Accounting Backlog, Accounting Usability & Engagement, Accounting Multi-ERP Provider Support, Accounting Tech Debts (bugs and tech debt) |
| jeeves-ai | EPD - Accounting ERP (`ACC`) | Accounting Usability & Engagement |
| jeeves-web | EPD - Accounting ERP (`ACC`) (confirmed for accounting-v2 work; other areas of jeeves-web may map to different teams) | Accounting Usability & Engagement |
| backend | Product - Wallet (`WAL`) | Jeeves Embedded Wallet Solution (Privy) |
| stablecoin-service | Product - Wallet (`WAL`) | Jeeves Embedded Wallet Solution (Privy) |

No row yet for a repo — resolve team/project live per the skill's
"Team, project, estimate, cycle" section, then add a row here from the
confirmed result.
