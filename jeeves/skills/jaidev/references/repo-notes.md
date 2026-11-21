# Repo notes for agent briefs

Facts agents found while running tickets, one section per repo. Paste the repo's section into the brief template's "Repo facts" part. After each merge, append the agent's "Repo facts learned" to this file in the same turn (`references/write-back.md` at the plugin root), and keep each section to the facts a new agent would otherwise rediscover. For a repo with no section yet, add one after its first merge.

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

## jeeves-web

- **Coverage gate:** `jest.config.js` holds a 100% global threshold, and CI runs `npm run test:cov` as **Unit Test** (~38 min per push). A single uncovered line fails the PR even when every suite passes (ACC-1697: 99.99%).
- **Single test file:** coverage off, so the global threshold does not fail a one-file run.

  ```bash
  npx jest --ci --coverage=false --runTestsByPath <file>
  ```

- **ts-lint memory:** Jaidev's sandbox ran out of heap at 2 GB; brief the larger heap.

  ```bash
  NODE_OPTIONS=--max-old-space-size=6144 npm run ts-lint
  ```

- **CI check names:** `Lint and Type Check`, `Unit Test`, `SonarCloud Code Analysis`, `Validate Localization`, `lint / Validate PR title`, `test / Scan for secrets`. `test / Unit Test` and `test / Code Analysis` show as skipped.
- **Validate Localization:** compares locale files with Crowdin and fails on new pt-BR or es-MX strings until a human runs `npm run crowdin-push`. It is not required to merge; brief it as a known failure.
- **SonarCloud:** scans `src` only, so keep logic out of `app/`. S2068 flags any object key containing "password" set to a string literal, even in a mock (ACC-1697 renamed `submitPassword` to `submitCredentials`).
- **Repo rules:** follow jeeves-web's CLAUDE.md (react-i18next copy, CSS modules with CSS variables and no fallbacks, `renderWithContext`, regex accessible queries, `userEvent`, no mocking of react-i18next or TanStack Query). `src/utils/config.ts` imports bootstrap data-access hooks, so a server `page.tsx` reads env flags through a small server-safe helper instead.
- **Parallel sibling tickets:** give each screen its own folder test and find steps in shared tests by an accessible region name, not placeholder text, so siblings edit no shared test.
