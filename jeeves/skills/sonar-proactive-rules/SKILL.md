---
name: sonar-proactive-rules
description: SonarCloud "Sonar way" TypeScript rules to write to proactively in Jeeves backend Node/TS services, so PRs pass the quality gate clean. Trigger when writing or editing TypeScript in a Jeeves repo, or when a Sonar issue cites a rule id (grep references/sonar-ts-rules-catalog.md by id).
---

# SonarCloud proactive rules — Jeeves TypeScript

Jeeves TS microservices run SonarCloud (org `jeevesinc`, profile **Sonar way** = default, 443 active TS rules) on every PR. The quality gate requires **0 New Issues** AND a **Coverage on New Code** condition to clear — every condition must pass, but the coverage threshold is set per-project (read it from the gate's own `errorThreshold`, e.g. `api/qualitygates/project_status`, rather than assuming a fixed number). Projects are private, so reading issue messages needs a token (see the `sonar-fix` skill) — writing to these rules up front is cheaper than fixing after.

The full 443-rule list lives in `references/sonar-ts-rules-catalog.md` — grep it by rule id (e.g. `S6582`) when an issue cites one not covered below.

## Rules that shape backend Node/TS code

**Modern API / idiom preferences (the S77xx family, very frequently triggered):**
- S7776 — a constant used only for membership checks should be a `Set` + `.has()`, not an array + `.includes()`.
- S6582 — prefer optional chaining: `obj?.prop`.
- S6606 — prefer nullish operators: `x ??= f()` and `a ?? b`.
- S6661 — prefer object spread over `Object.assign`; S6666 — spread over `.apply()`; S7747 — keep spread to where it's actually needed.
- S7765 — prefer `.includes()` over `.indexOf() >= 0`; S7754 — prefer `.some()` over `.filter().length`/`.find()` for existence checks; S7750 — prefer `.find()` over `.filter()[0]`; S7752 — prefer `.flatMap()` over `.map().flat()`; S7751 — prefer `.flat()`.
- S7759 — prefer `Date.now()` for timestamps; S7719 — clone `Date` objects directly, no `getTime()`; S7741 — compare directly with `x === undefined`; S6557 — prefer `startsWith`/`endsWith`; S7781 — prefer `replaceAll()`; S7772 — prefer the `node:` protocol for builtins; S7773 — prefer `Number.*` over global equivalents; S6590 — prefer `as const`.
- S4634 — return the promise directly (no `async` wrapper); S7746 — return/throw the value directly inside an async function or promise callback; S4123 — `await` only on promises.

**Complexity & structure:**
- S3776 — keep cognitive complexity ≤ 15 per function (each if/for/catch/ternary + each `&&`/`||` adds a point; nesting multiplies) — extract helpers to lower it. S2004 — keep functions shallow, flattening nested definitions; S107 — keep parameter counts low; S3358 — keep ternaries single-level, extracting a nested one into if/else or a helper; S1871/S4144 — give each branch/function a distinct implementation, extracting shared logic into one helper; S1192 — hoist a string literal repeated ≥3×.

**Correctness / cleanup:**
- S1128 — remove unused imports; S1854/S1068 — remove unused assignments/private members; S2486 — act on every caught exception (log it, rethrow it, or handle it); S3696 — throw `Error` objects, not literals; S1125 — write the boolean check directly, e.g. `if (x)`; S6509 — use the boolean value as it is; S6564 — use the type directly instead of aliasing it redundantly; S2933 — mark constructor-only fields `readonly`; S6550 — use literal enum members; S878 — separate statements with semicolons instead of the comma operator.

**Frontend-only rules, out of scope for these backend services:** React/JSX (S64xx/S67xx), Angular (S76xx), Vue (S89xx), DOM/accessibility (S68xx) — they're in the catalog but backend repos don't hit them.

## Coverage gate

Any file in the jest.config `coveragePathIgnorePatterns` (entry points `start-*.ts`, `main.ts`, `server.ts`, barrels) must also be listed in `sonar.coverage.exclusions` in `sonar-project.properties` — otherwise Sonar counts it as 0%-covered new code and the gate drops below 100%. Keep both lists in sync when adding a bootstrap/entry file.
