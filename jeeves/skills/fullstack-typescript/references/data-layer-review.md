# Data-layer review

Checks for the types, repositories and error handling of a Sequelize/TypeScript service, read alongside `review-checklist.md`. Each row states the shape to keep and the symptom to flag. The last group lists the bugs these symptoms cause, so a review that finds a symptom also looks for its bug.

Gathered from the accounting-service Doc 0 data-model rework (PR #620 and its stack); the examples come from there.

## Types

| # | Keep | Flag |
|---|---|---|
| 1 | Written-out interfaces and DTO classes | Types built from `Pick`, `Omit`, `Partial<Pick<…>>` or `&` intersections |
| 2 | A join modelled as nested objects, one per table | Two tables flattened into one object with renamed or overwritten fields (`companyStatus`, `Omit<…, 'companyId'>`) |
| 3 | One type per shape | Several types for one shape (`…Row`, `…WithX`, DTO copies), or a type used only as a cast target |
| 4 | TypeScript nullability that matches the column | A non-null type on a nullable column, or the reverse |
| 5 | API responses as explicit DTO classes | Response types derived from model attributes |

## Data access

| # | Keep | Flag |
|---|---|---|
| 6 | Model instances, or rows mapped through one explicit mapper | `as unknown as` casts, especially on `raw: true, nest: true` results |
| 7 | Each repository queries its own table; the repository folder holds repositories only | A repository querying another model's table; helpers, include builders or exported utilities in the repository folder |
| 8 | One method per query | Duplicate or alias methods that run the same query under different names |
| 9 | Reads from the column that owns the value | Reads of retired columns (`integration.companyId` instead of `integration_companies.companyId`) |
| 10 | `required` flags chosen per caller, with skipped rows handled | Joins that silently drop rows, or keep rows callers cannot handle (`required: true` vs `required: false`) |

Named, reusable includes belong in model scopes (`Model.addScope`), defined next to the associations they use.

## Naming and signatures

| # | Keep | Flag |
|---|---|---|
| 11 | One verb rule: `find…` returns `null` or `[]`, `get…` throws, writes use `create`, `update…`, `delete…` | Mixed verbs (`get` / `find` / `fetch`, `sync` for an `UPDATE`, `softDelete`), or names that misdescribe the query |
| 12 | Filters passed as arguments | Hard-coded values in method names (`…Codat`) where sibling methods take a filter |
| 13 | `{ transaction }` as the last argument everywhere | `transaction` positional in some methods and an options object in others |
| 14 | One meaning per word | One word with two meanings ("current" as a status set and as "not deleted") |

## Logic

| # | Keep | Flag |
|---|---|---|
| 15 | One source per rule, with derived values computed in code | One idea as two lists that can drift, or derived constants nobody can trace |
| 16 | Computed values computed where they are read; branches only for reachable states | Computed values stored on types (`category`), or branches for impossible states (NULL handling on non-null data) |
| 17 | Each rule in one place | The same rule implemented differently in two files ("NULL means ERP" here, "throw on NULL" there) |

## Errors

| # | Keep | Flag |
|---|---|---|
| 18 | Repositories translate database errors into named domain errors | Services catching database errors and classifying them through a repository; catch-and-rethrow repeated across methods |
| 19 | Constants and error classes in the file of their scope | An index name kept in another table's repository; an error class in an unrelated module |
| 20 | Named domain errors that carry their HTTP status | Ad hoc `BadRequestError` where a named domain error belongs |

## Bugs these symptoms cause

| # | Check for | Typical cause |
|---|---|---|
| 21 | `uniqBy`, `groupBy` or `Map` keyed on an `id` that now names a different entity | Symptom 2: after a type change, `id` moved from the integration to the company link |
| 22 | Write paths copying a value from the wrong table (`companyId` taken from `integration`) | Symptoms 2 and 9 |
| 23 | HTTP status codes or webhook retry behaviour that changed without a decision | Symptoms 18 and 20: an error now thrown outside a `try`, or mapped to a 4xx that stops retries |

## Finding format

Use the format in `review-checklist.md`, and name the symptom number with each finding.
