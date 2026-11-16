# Naming tables

Casing, class and interface, function and method, and variable conventions.

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
- Use the layer suffixes the target repo already uses, consistently: `Service`, `Repository`, `Controller`, `Client`, `Mapper`, `Factory`, `Dto`, `Error`.
- Give abstract base classes one prefix style (`Base…` or `Abstract…`) across the target repo.

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
