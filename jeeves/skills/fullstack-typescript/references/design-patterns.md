# Low-level design and patterns

Start from plain functions and data. Add a pattern when it removes a named problem.

## Boundaries

- Give each module one reason to change and a small public surface.
- Point dependencies inward: domain logic imports nothing from HTTP, the database or a vendor SDK.
- Keep I/O at the edges: a handler parses input, calls pure domain logic, then persists and responds.
- Pass dependencies as constructor or function parameters; build the object graph once, at startup.
- Compose behaviour from small functions and objects; reserve inheritance for a true "is-a" with shared state.

## Model the domain

- Make illegal states unrepresentable: one discriminated union instead of several optional fields and flags.
- Parse once at the boundary into a domain type; inside, values are already valid.
- Give distinct meanings distinct types (`WalletId` and `UserId` as branded strings).
- Keep data immutable by default (`readonly`, new objects for changes).

## Errors

| Kind | Handling |
|---|---|
| Expected outcome the caller acts on (insufficient funds, not found) | Return it as a typed result: `{ ok: true, value } \| { ok: false, error }` with a discriminated `error` |
| Broken invariant or programmer error | Throw; let one top-level handler log and respond |
| Failure in a dependency | Wrap with context (`cause`) at the adapter, map to a domain error |

Use one style per layer, and handle or propagate every rejected promise.

## Patterns

| Pattern | Use when | Skip when |
|---|---|---|
| Strategy (a map of functions) | Several interchangeable algorithms chosen at runtime | Two cases that an `if` covers |
| Adapter | Wrapping a vendor SDK or legacy API behind your own interface | The call is used once and is stable |
| Repository | Domain logic needs persistence without knowing the store | A simple CRUD handler over an ORM |
| Factory | Construction needs validation, defaults or a choice of implementation | `new X(args)` is clear |
| Decorator / middleware | Adding caching, retries, metrics or auth around a function | The concern applies in one place |
| Observer / events | Several independent reactions to one fact | One caller and one reaction; call it directly |
| State machine | An entity has named states and legal transitions | A boolean flag describes it |
| Builder | Many optional parameters with rules between them | An options object with defaults works |
| Command | Operations must be queued, retried, audited or undone | The operation runs once, inline |
| Specification / policy object | Business rules combine and get reused | A single predicate |

In TypeScript most patterns are a function type, a record of functions or a discriminated union; reach for a class when there is state with invariants.

## Low-level design template

1. Modules and their responsibilities
2. Public types and function signatures per module
3. Patterns chosen, each with the problem it removes
4. Error model per layer
5. Test seams (what is injected, what is pure)
