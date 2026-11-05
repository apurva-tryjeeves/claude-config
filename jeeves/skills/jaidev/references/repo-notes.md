# Repo notes for agent briefs

Facts agents found while running tickets, one section per repo. Paste the repo's section into the brief template's "Repo facts" part. After each merge, append the agent's "Repo facts learned" here in the same turn, and keep each section to the facts a new agent would otherwise rediscover. For a repo with no section yet, add one after its first merge.

## accounting-service

- **Single test file:** run it with `--runTestsByPath`; a bare path under `--selectProjects unit` runs all 2,241 tests.

  ```bash
  NODE_ENV=test npx jest --ci --coverage=false --selectProjects unit --runTestsByPath <file>
  ```

- **Lint:** `npm run lint` ends with 4 warnings and 0 errors, and the limit is 5. `npm run ts-lint` must pass. Fix touched test files first, because a long `mockResolvedValue` line breaks prettier:

  ```bash
  npx eslint --fix <touched-test-files>
  ```

- **Unused destructured fields:** `jeeves-eslint-config` leaves `ignoreRestSiblings` unset, and an `_` prefix still trips `no-unused-vars`. Wrap the helper in one `eslint-disable` and `eslint-enable` block with a one-line reason.
- **Golden tests:** `src/services/__tests__/*.golden.test.ts` and `src/services/account/__tests__/*.golden.test.ts` pin today's behaviour. A ticket that changes behaviour updates them and the PR calls the change out.
- **DB-backed tests:** a few tests need a real MySQL (testcontainers). They fail in Jaidev's sandbox and pass in CI `test / Unit Test`.
- **Reading code:** read the parent branch this way; the main checkout stays on its own branch.

  ```bash
  git -C <main-checkout> show origin/<parent>:<path>
  ```

- **CODEOWNERS:** the feature parent branches carry none, so only the user's approval applies.
- **Jaidev's test run:** its sandbox has no Docker, so it runs a single test file with a temporary jest config outside the repo that drops `globalSetup` and `globalTeardown`. CI `test / Unit Test` is the authoritative run.
- **Extra tests:** Jaidev adds tests beyond the briefed ones when its self-review flags an untested branch (ACC-1634: 38 tests against 35 briefed). They are in scope when they stay in the briefed files.
- **Logging errors:** `originalError` on `ErpProviderError` is enumerable and the port-call wrapper logs `err: providerError`, so a message sanitized alone still leaks `config.headers`. Sanitize `originalError` too and keep the raw error on the non-enumerable `providerCause`.
- **pino and errors:** pino applies its Error serializer only to the `err` key, so a second Error under another key serializes as `{}`. Log it as a string built with `stringifyError` outside the logger call (lint rule R4).
- **Non-enumerable fields:** `useDefineForClassFields` is off, so a declared class field without an initializer emits nothing. `readonly cause?: unknown` plus a guarded `Object.defineProperty` stays non-enumerable, and ts-lint needs no `override`. `ErpProviderError` carries `cause` (ACC-1636) next to the non-enumerable `providerCause`.
- **Plan reviews of cleanups:** check each import change against the whole file (ACC-1645 v1 would have dropped an `ErpPlatform` import that `resolveForNewConnection` still uses, which fails ts-lint).
- **Repository methods:** `getTransactionsByTransactionIds(companyId, ids)` and `getByIdOrCode(companyId, value)` are the company-scoped lookups; the older `getTransactionById` and `getById` are unscoped.

authoring-guide: v4
