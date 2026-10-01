# Data flow

## Target pipeline (planned unless marked)

```text
Source (URL/transcript/file)
  → SourceExtractor → NormalizedSource            [interface + YouTube URL validation]
  → Transcript → chunks → embeddings → pgvector   [tables + chunking; embedding workflow planned]
  → analysis → story arcs → script (versions)     [planned]
  → SceneSpec[] (storyboard)                      [schema implemented]
  → characters / locations / visual bible         [tables; generation planned]
  → images (ImageGenerator) + voice (VoiceProvider) → Assets   [interfaces]
  → build_timeline(SceneSpec[]) → Timeline JSON   [implemented]
  → Remotion composition → MP4                    [implemented for the sample]
  → QA                                            [planned]
```

## The timeline contract

`app.schemas.scene.Timeline` (Python, source of truth) ⇄ `packages/video/src/types.ts` (zod mirror) ⇄
`packages/schemas/timeline.schema.json` (generated). Scenes carry `start`, `duration`, `subtitle`, optional
`image_src`/`audio_src`, and `camera.movement`. Durations come from code: measured audio length when
available, otherwise `estimate_duration` (clamped 2–7 s as a *default*, not a rule).

Render today: `pnpm --filter @storyweaver/video render` reads `sample/timeline.json` → `out/sample.mp4`.
Live preview: `/studio` embeds the Remotion Player with the same JSON.

## Retry and idempotency (design intent)

Operations are keyed by entity id (`import_video(video_id)`, `generate_scene_image(scene_id)`,
`render_project(project_id)`): they read current state, skip finished work, and write `status` + `error`
on the entity. `LocalRunner` logs `workflow_id`/status and never lets a failed job crash the app. None of these
operations exist yet.

## Semantic search (planned)

`transcript_chunks.embedding` + HNSW cosine index are in place and covered by a nearest-neighbour test.
`chunk_segments` produces timed chunks. Embedding generation and RAG endpoints are not built.
