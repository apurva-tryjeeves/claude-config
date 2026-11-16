# Codebase structure

Follow the target repo's existing layout first. Apply these rules to new modules and to repos with no stated layout.

## Shared rules

- Organize by feature or domain first, by technical layer inside it.
- Keep one main export per file, and name the file for it (`jeeves:typescript-naming`).
- Import a feature through its public entry file; its internals stay private to it.
- Keep dependencies acyclic; shared code moves down into a lower module.
- Put a test beside the unit it covers; put cross-module tests in one integration folder.
- Create a shared utility on its third use.
- Read configuration once at startup, validate it with a schema, and pass typed values inward.

## Backend service

```text
src/
  <feature>/
    <feature>.routes.ts        HTTP wiring: parse, call, respond
    <feature>.service.ts       use cases and orchestration
    <feature>.domain.ts        pure rules and types
    <feature>.repository.ts    persistence behind an interface
    <feature>.schemas.ts       input and output schemas
    <feature>.test.ts
  platform/                    db, queue, http client, logger, config
  app.ts                       builds the dependency graph
  server.ts                    starts and stops the process
```

| Layer | May import |
|---|---|
| routes | service, schemas |
| service | domain, repository interfaces, platform interfaces |
| domain | nothing outside the feature's domain |
| repository | platform (db), domain types |

- Keep handlers thin: validation, one service call, response mapping.
- Keep transactions in the service layer, opened and closed in one function.
- Wrap each external system in one adapter module under `platform/`.

## React application

```text
src/
  features/<feature>/
    components/      presentational pieces
    hooks/           behaviour and data hooks
    api/             typed requests and query keys
    <Feature>Page.tsx
    index.ts         public surface
  shared/            design-system components, hooks, utils
  app/               routing, providers, layout
```

- Keep data fetching in hooks under `api/` or `hooks/`; components receive data and callbacks.
- Share types with the backend from one generated or shared contract package.
- Co-locate styles, tests and stories with the component.
- Split routes with lazy loading; keep the shared bundle small.

## Module checklist

- Can a new engineer find the entry point of this feature from its folder name?
- Does deleting the feature folder remove the feature with few edits elsewhere?
- Does any file import from another feature's internals?
