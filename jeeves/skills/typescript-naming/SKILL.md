---
name: "typescript-naming"
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

## Casing

| Construct | Case | Example |
|---|---|---|
| Class | PascalCase noun | `PaymentProcessor` |
| Interface | PascalCase contract name, starting with the domain word | `ErpProvider`, `Serializable` |
| Type alias | PascalCase | `WalletId`, `TransferResult` |
| Enum | PascalCase singular; PascalCase members | `TransferStatus.Pending` |
| Generic parameter | `T`, or `T` + PascalCase | `T`, `TResponse`, `TKey` |
| Function, method | camelCase verb phrase | `createTransfer` |
| Variable, parameter, property | camelCase noun | `walletId` |
| Module-level true constant | UPPER_SNAKE_CASE | `MAX_RETRIES` |
| Local `const` | camelCase | `const user = …` |
| Private member | camelCase with `private` or `#` | `private cache` |
| File | kebab-case matching the main export | `payment-processor.ts` |

## Classes and interfaces

- Name a class for its single role: `TransferService`, `CodatClient`, `LedgerMapper`.
- Name the interface for the contract and each implementation for how it fulfils it: `ErpProvider` → `CodatErpProvider`, `InMemoryErpProvider`.
- Use the layer suffixes this repo already uses, consistently: `Service`, `Repository`, `Controller`, `Client`, `Mapper`, `Factory`, `Dto`, `Error`.
- Give abstract base classes one prefix style (`Base…` or `Abstract…`) across the repo.

## Functions and methods

Start with a verb that signals intent and cost:

| Verb | Meaning |
|---|---|
| `get` | cheap, local, returns a value |
| `fetch` / `load` | I/O, async |
| `find` | may return `undefined` / `null` |
| `create` / `build` / `make` | produces a new instance |
| `to` / `from` / `parse` / `format` | conversion |
| `validate` | returns a result |
| `assert` / `ensure` | throws on failure |
| `handle` / `on` | event or message handler |

- Let the class supply the object: `wallet.getBalance()`.
- Name async functions by what they return; add an `Async` suffix only when a sync twin exists.
- Phrase boolean-returning functions as a question: `isExpired()`, `canWithdraw()`.

## Variables

- Booleans: `is` / `has` / `can` / `should` prefix, phrased positively (`isEnabled`).
- Collections: plural (`transfers`). Maps: `valueByKey` (`walletById`, `balanceByCurrency`).
- Bare numbers carry their unit: `timeoutMs`, `amountMinor`, `ttlSeconds`.
- Length scales with scope: `i` in a short loop, `pendingTransferIds` across a function.
- Spell words out; keep only universal abbreviations (`id`, `url`, `api`, `db`).
- Write acronyms as words: `HttpClient`, `userId`, `parseJson`.

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
- PR review: use the report shape in `references/pr-review.md`.
- Keep the reply to these items; usage examples, restated conventions and closing questions stay out.

authoring-guide: v4
