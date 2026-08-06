# Frontend QA

When `apps/web` is in scope:

```bash
cd apps/web
npm ci   # if needed
npm run lint
npm run build   # or project typecheck + build scripts from package.json
```

## Require

- Lint clean
- Typecheck clean (if configured)
- Production build succeeds
- Error/empty/loading states for touched flows (no silent blank failures)
- API contract alignment with backend schemas (no calling removed fields)

## Reject

- “UI looks fine” without build
- Ignoring TypeScript errors
- Shipping dead CTAs / placeholder copy on in-scope production routes (escalate quality to `/ceo`)
