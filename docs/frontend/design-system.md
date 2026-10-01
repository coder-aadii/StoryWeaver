# Frontend Design System

> Visual foundations used by the web app.

## Status

**Partially implemented.** A stock shadcn/ui setup exists; a StoryWeaver-specific visual identity is *Decision pending*.

## Foundations

- **Tailwind CSS 4** with CSS variables in `src/app/globals.css` (shadcn tokens: background, foreground, card, primary, muted, accent, destructive, border, sidebar-*), expressed in `oklch`.
- **Dark mode**: a `@custom-variant dark` and dark token set exist, but there is **no theme toggle**; the app follows the light defaults unless a `.dark` class is applied.
- **Fonts**: Geist Sans and Geist Mono through `next/font/google`, exposed as `--font-geist-sans` / `--font-geist-mono` and mapped to `--font-sans`. (Fetching fonts needs network at dev/build time — [KI-25](../reference/status.md#known-issues-and-limitations).)
- **Icons**: `lucide-react`.
- **Primitives**: shadcn `button`, `card`, `badge`, `table`, `skeleton`.
- **Utility**: `cn()` in `lib/utils.ts` (clsx + tailwind-merge).

## Patterns

Page = `PageHeader` + content; cards for summaries; bordered table for lists; badges for status; dashed-border empty state; destructive-tinted alert for errors; skeleton rows for loading. Spacing uses Tailwind scale; main content padding `p-6`.

## Rules

- Use tokens (`bg-background`, `text-muted-foreground`), not raw colours.
- New primitives come from shadcn; keep generated files unmodified where possible.
- Prettier with `prettier-plugin-tailwindcss` orders classes (`pnpm --filter @storyweaver/web format`).

## Not done

Theme switcher, brand palette, typography scale doc, responsive tables, motion guidelines, accessibility contrast review. Planned — not implemented.

Related: [component-architecture.md](component-architecture.md).
