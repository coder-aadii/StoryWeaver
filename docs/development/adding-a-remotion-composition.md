# Adding a Remotion Composition

> How to add or change a video composition in `packages/video`.

## Status

Implemented (one composition, `Basic`).

## Layout

- `src/BasicComposition.tsx` — the React composition; one `<Sequence>` per timeline scene.
- `src/Root.tsx` — registers `<Composition id="Basic" ...>` with `calculateMetadata` deriving duration/fps/size from props.
- `src/types.ts` — zod mirror of the Python `Timeline` (`timelineSchema`).
- `src/camera.ts` — pure `cameraTransform(movement, t)`.
- `src/entry.ts` — `registerRoot`; `src/index.ts` — exports consumed by the web Player.
- `sample/timeline.json` — props for `pnpm render`.

## Steps for a new composition

1. Create `src/<Name>Composition.tsx` accepting `Timeline` props (keep the JSON-in contract; no data fetching inside compositions).
2. Register another `<Composition id="<Name>" .../>` in `Root.tsx`.
3. Keep logic pure and deterministic: no `Math.random`, no wall-clock; derive everything from `useCurrentFrame()` and props.
4. If the contract changes: edit Python `app/schemas/scene.py`, run `make schemas`, then mirror in `types.ts`. There is no automated drift check between them — Decision pending.
5. Tests: unit-test pure helpers and `timelineSchema.parse(sample)` in `src/*.test.ts`.
6. Render: add a script or pass the composition id: `remotion render src/entry.ts <Name> out/x.mp4 --props=./sample/timeline.json`.
7. Preview in the web app: export it from `src/index.ts` and use `@remotion/player` as in `apps/web/src/app/studio/page.tsx`.

Notes: remote image/audio URLs must be reachable by the render browser; Remotion licensing is the owner's decision ([README](../../README.md)). See [Remotion](../media/remotion.md), [timeline specification](../media/timeline-specification.md).

> Working as an AI coding agent? Read [AI agent guide](ai-agent-guide.md) first.
