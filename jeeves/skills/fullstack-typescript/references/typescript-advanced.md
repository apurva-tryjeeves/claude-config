# TypeScript: advanced features and when they pay

Apply the judgement test from `SKILL.md` to each feature. Check the repo's TypeScript version before using a version-gated one.

## Modelling

| Feature | Use when | Keep plain when |
|---|---|---|
| Discriminated union + `never` exhaustiveness | A value has distinct shapes or states; adding a case must break the build | Two shapes handled in one place |
| Branded type (`string & { readonly __brand: 'WalletId' }`) | Ids, money or units that must stay unmixed across a wide surface | A value used inside one function |
| `as const` + derived union (`typeof X[number]`) | One list drives both runtime values and the type | The union has no runtime use |
| `satisfies` (4.9) | Checking an object against a type while keeping its literal types | A plain annotation loses nothing |
| `readonly` / `ReadonlyArray` | Data shared across modules | Local scratch values |
| Template literal types | Keys or event names follow a pattern | Free-form strings |
| `enum` alternative: `as const` object | Values need runtime presence and a union type | The repo standardizes on `enum` |

```ts
type Transfer =
  | { status: 'pending' }
  | { status: 'settled'; settledAt: Date }
  | { status: 'failed'; reason: string };

function label(t: Transfer): string {
  switch (t.status) {
    case 'pending': return 'Pending';
    case 'settled': return `Settled ${t.settledAt.toISOString()}`;
    case 'failed': return `Failed: ${t.reason}`;
    default: { const unreachable: never = t; return unreachable; }
  }
}
```

## Keyed data: `Record`, `Map`, index signature

| Choice | Use when |
|---|---|
| `Record<Union, V>` | Keys are a known finite union; the compiler then requires every key |
| `Partial<Record<Union, V>>` | Known keys, some absent |
| `Map<K, V>` | Keys are dynamic or user-supplied, non-string, need ordering or frequent add and delete |
| `Record<string, V>` | A JSON-shaped dictionary from a trusted source; enable `noUncheckedIndexedAccess` so a lookup is `V \| undefined` |
| `Set<T>` | Membership checks |

A strategy table as `Record<Kind, Handler>` gives exhaustive dispatch with no `switch`.

## Generics and type-level tools

- Add a type parameter when it relates two positions (input to output); a parameter used once is a plain type.
- Constrain parameters (`<T extends { id: string }>`) and give defaults where they help callers.
- Derive types from one source: `Pick`, `Omit`, `Partial`, `Required`, `ReturnType`, `Parameters`, `Awaited`, `z.infer`.
- Use mapped and conditional types, `infer` and `keyof` inside shared library modules; export a simple named type from them.
- Use overloads or a discriminated options object when the return type depends on the input.
- `const` type parameters (5.0) and `NoInfer` (5.4) fix inference at a call site; add them when a caller would otherwise annotate.

## Boundaries

- Type external data as `unknown`, validate with a schema, and derive the static type from it.
- Narrow with type guards (`x is T`) and assertion functions (`asserts x is T`).
- Replace `any` with `unknown` or a generic; replace `as` casts with a guard, and comment the rare cast that stays.
- Annotate exported functions' parameters and return types; let inference work inside.

## Language features

| Feature | Use for |
|---|---|
| `??`, `?.` | Defaults and optional access on nullable values |
| `using` / `await using` (5.2) | Scoped cleanup of locks, connections, temp files |
| Generators and async iterators | Paging through large result sets lazily |
| `Promise.allSettled` and bounded pools | Fan-out where partial failure is expected |
| `structuredClone` | Deep copies of plain data |
| `WeakMap` | Per-object caches that follow the object's lifetime |
| `Object.freeze` + `as const` | Shared constant tables |
| Error `cause` | Wrapping a failure while keeping the original |

## Compiler settings to favour

`strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`, `noFallthroughCasesInSwitch`, `useUnknownInCatchVariables`.
