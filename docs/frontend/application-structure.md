# Frontend Application Structure

> Where things live in `apps/web` and the conventions to follow when adding code.

## Status

**Implemented** (as a foundation).

## Layout

```text
apps/web/
├── src/
│   ├── app/                    App Router pages (all under the shared layout)
│   │   ├── layout.tsx          fonts, metadata template, <Providers><AppShell>
│   │   ├── page.tsx            redirect("/dashboard")
│   │   ├── dashboard/ sources/ (channels/, videos/) topics/ collections/
│   │   ├── projects/ (page.tsx, [id]/page.tsx)  studio/  settings/
│   │   └── globals.css         Tailwind 4 + shadcn CSS variables
│   ├── components/
│   │   ├── app-shell.tsx  api-status.tsx  page-header.tsx  providers.tsx
│   │   ├── resource-list.tsx  states.tsx  status-badge.tsx
│   │   └── ui/                 shadcn primitives: badge, button, card, skeleton, table
│   └── lib/                    api.ts (client + types), store.ts (Zustand), format.ts, utils.ts (cn)
├── e2e/navigation.spec.ts      Playwright
├── vitest.config.ts  vitest.setup.ts  playwright.config.ts
├── next.config.ts              transpilePackages: ["@storyweaver/video"]
└── AGENTS.md / CLAUDE.md       scaffold files from Next.js (agent hints)
```

## Conventions

- `@/` alias maps to `src/`.
- Pages that pass render functions (e.g. table `columns`) to `ResourceList` are **client components** (`"use client"`), because functions cannot cross the server→client boundary. Pages with static content (`/sources`) stay server components and export `metadata`.
- Server state goes through TanStack Query; UI-only state through Zustand ([state-management.md](state-management.md)).
- Shared domain types currently live in `lib/api.ts` (Project, Health, Ready, ProviderHealth); simple list pages declare local interfaces. A generated TypeScript client from OpenAPI is *Decision pending*.
- Do not edit `components/ui/*` by hand-formatting; the Prettier ignore file excludes it. Add primitives with `pnpm dlx shadcn@latest add <name>`.
- The workspace package `@storyweaver/video` is consumed as TypeScript source.

## Build and scripts

`dev` (port 3100), `build`, `start`, `lint` (ESLint), `typecheck` (`tsc --noEmit`), `test` (Vitest), `test:e2e` (Playwright), `format` / `format:check` (Prettier with Tailwind plugin). `next build` succeeds and prerenders all static routes; `/projects/[id]` is dynamic.

## Failure modes and limitations

`next/font/google` fetches fonts at build/dev time, so a fully offline first build can fail — *Decision pending* on self-hosting fonts. Tracked as [KI-25](../reference/status.md#known-issues-and-limitations). Environment: `NEXT_PUBLIC_API_URL` is inlined at build time and must be set in `apps/web/.env.local` or the shell (see `apps/web/.env.example`), not the root `.env`; the dev/start scripts bind to `127.0.0.1`.
