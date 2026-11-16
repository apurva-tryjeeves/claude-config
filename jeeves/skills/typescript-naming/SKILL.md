---
name: typescript-naming
description: TypeScript naming conventions for identifiers and files. Use whenever planning TS or Node.js work (plan mode, implementation plans, design docs, specs, RFCs, ticket breakdowns) so new names are settled before code, when writing new TS code, and when reviewing or renaming identifiers in a pull request. Applies whether or not naming is mentioned.
---

# TypeScript naming

Apply these conventions when planning TypeScript work, and to every identifier you create or rename in code.

## During planning

Settle names in the plan so implementation picks them up verbatim.

1. Read the repo rules and scan the modules the plan touches (see *Order of precedence*) to learn the existing vocabulary and layer suffixes.
2. Add a **Names** section to the plan with one row per new identifier that crosses a file or module boundary — classes, interfaces, types, enums, exported functions, methods on public classes, files, and module-level constants:

   | Kind | Name | File | Purpose |
   |---|---|---|---|
   | interface | `ErpProvider` | `src/providers/erp-provider.ts` | Contract every ERP integration implements |
   | class | `CodatErpProvider` | `src/providers/codat-erp-provider.ts` | Codat implementation of `ErpProvider` |
   | method | `fetchInvoices` | `ErpProvider` | Loads invoices from the ERP (I/O) |

3. When you settle a repo-wide choice the repo rules have yet to record (its layer suffixes, `Base…` or `Abstract…`, `remove` or `delete`), list it under **Names** as a proposed `AGENTS.md` addition, so the next session reads it there.
4. List renames of existing identifiers separately as `Old name → New name`, and flag any that touch a public contract for the user to decide.
5. Leave local variables and private helpers to implementation time; the conventions below cover them.

## During implementation

- Use the names from the plan's **Names** section exactly.
- Name anything the plan left open by the conventions below.
- When a planned name turns out wrong once the code takes shape, pick the better name and note the change in your summary.

## Order of precedence

1. Repo-specific rules in `AGENTS.md`, `CLAUDE.md` or `CONTRIBUTING.md` — read these first and follow them.
2. Vocabulary already dominant in the surrounding code (e.g. the repo uses `fetch` → use `fetch`).
3. The conventions below.

## Naming tables

The casing table, the class and interface suffix rules, the function verb table and the variable rules live in `references/naming-tables.md`. Read it when naming a new identifier or file.

## Consistency

- Use one word per concept across the codebase (`remove` or `delete`, `customer` or `client`).
- Use the domain terms from the product, tickets and docs so code and docs read the same.
- Name tests by behaviour: `it('rejects a transfer when balance is insufficient')`.

## Public contracts

Keep exported package APIs, HTTP routes and payload fields, DB columns, event names, env vars and queue topics stable. Raise a naming issue in these as a recommendation for the user to decide.

## Reviewing a pull request

When asked to review or fix naming in a PR, read `references/pr-review.md` and follow its workflow.

## Reporting results

- Planning: the **Names** table is the plan's whole naming output.
- Writing new code: deliver the code; mention naming only when you followed a repo rule that differs from these conventions.
- PR review request: report the proposed-renames table (`File | Old name | New name | Rule applied`), the recommendations for public-contract names kept unchanged, and the verification commands run with their pass status; apply renames only when asked to fix. When nothing needed renaming, reply with one line saying so plus the verification status. Add one line when a check fails for a reason outside the PR, naming the check and its cause.
- Keep the reply to these items; usage examples, restated conventions and closing questions stay out.
