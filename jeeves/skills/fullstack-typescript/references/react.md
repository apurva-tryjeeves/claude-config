# React

## State placement

| State | Lives in |
|---|---|
| Server data | A query cache (the repo's data-fetching library), keyed and invalidated by mutation |
| Shareable view state (filters, page, tab) | The URL |
| Form input | The form library or local state, validated by the shared schema |
| Local UI (open, hover, step) | `useState` in the nearest component |
| Cross-cutting client state (theme, session) | Context or a small store |

Keep state at the lowest component that needs it, and lift it when a second consumer appears.

## Rendering

- Compute derived values during render; store only the minimal source state.
- Give list items stable keys from the data.
- Keep component trees cheap first: split large components, pass children, move state down.
- Add `memo`, `useMemo` or `useCallback` after a profile shows a costly re-render or when a stable reference is required by a dependency array.
- Virtualize long lists; lazy-load routes and heavy components.
- Mark non-urgent updates with `useTransition` or `useDeferredValue`.

## Effects

- Use an effect to synchronize with something outside React: a subscription, a timer, a DOM API, a non-React widget.
- Handle user actions in event handlers, and data loading in the data-fetching library.
- Return a cleanup from every effect that subscribes or starts work, and cancel in-flight requests with an `AbortSignal`.
- List every reactive value in the dependency array; restructure the code when the list feels wrong.

## Composition

- Build small components with one job; pass content as `children` or render props to avoid long prop chains.
- Put behaviour in custom hooks (`useTransferForm`) and keep components mostly markup.
- Type props so wrong use fails to compile: discriminated unions for variants, required callbacks for controlled inputs.
- Wrap each route or widget in an error boundary with a recovery action.

## User-facing quality

- Design four states for every data view: loading, empty, error, success.
- Use semantic elements, labels, focus management and keyboard paths; check contrast.
- Give immediate feedback on actions; use optimistic updates where a rollback is simple.
- Prevent double submits and show server validation errors beside the field.
- Budget the bundle and watch the network waterfall: fetch in parallel, prefetch on intent, cache with HTTP headers.

## Testing

- Test behaviour through the rendered output and user events, querying by role and label.
- Mock at the network layer, so hooks and components run for real.
- Cover the four states and the main failure path of each feature.
