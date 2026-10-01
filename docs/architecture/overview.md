# Architecture overview

StoryWeaver is a **modular monolith**: one FastAPI application, one PostgreSQL database, one Next.js UI.
Domain modules live under `apps/api/app/` and talk through plain Python interfaces.

## Modules

| Module | Responsibility | State |
| --- | --- | --- |
| `ingestion` | `SourceExtractor` → `NormalizedSource`; YouTube URL validation + yt-dlp; transcription interface; transcript chunking | URL validation, chunking implemented; extraction/transcription need optional extras and are untested against real services |
| `intelligence` | `LLMProvider.generate/generate_structured`, `EmbeddingProvider.embed`, lazy registry | Adapters for Ollama, Google, OpenRouter, Grok, Claude-compatible |
| `story` | Story architecture (hook→resolution) | Placeholder |
| `visual` | `ImageGenerator` (ComfyUI stub, mock) | Interface |
| `voice` | `VoiceProvider` | Interface; fails loudly when unconfigured |
| `video` | Deterministic timeline builder | Implemented |
| `quality` | Automated QA | Placeholder |
| `workflows` | `WorkflowRunner`; `LocalRunner` in-process | Temporal adapter later |
| `core` | Settings, structured logging (key-name redaction), local storage with traversal protection | Implemented |

## Rules the code follows

- **Lazy everything.** Importing the app opens no connection and loads no model; providers are created on use.
- **Optional providers.** Missing keys make a provider "not configured", never crash startup.
- **AI vs. code.** LLMs produce `SceneSpec` content; `video.timeline` assigns durations/start times; Remotion/FFmpeg render.
- **Granular identity.** `Scene`, `SceneVersion`, `Asset`, `Render` have their own ids and statuses, with `error` persisted so a failure is retryable without touching the rest of the project.
- **Versioned content.** `ScriptVersion`, `SceneVersion` (unique `(parent, version)`), with `prompt_version`/`provider`/`model` recorded on scripts.
- **Binary data is not in Postgres.** `Asset.storage_key` points into `data/` (S3/MinIO later behind the same `Storage` protocol).
- **Shared sources.** `SourceVideo` is unique per `(platform, external_id)`; `ProjectSource` and `CollectionVideo` are join tables.

## Database

17 tables: `channels, source_videos, transcripts, transcript_chunks (vector(768), HNSW cosine index), topics,
collections, collection_videos, projects, project_sources, scripts, script_versions, scenes, scene_versions,
characters, locations, assets, renders`. Enums are stored as VARCHAR (not native PG enums) so adding a status
needs no `ALTER TYPE`. The embedding dimension (768) is fixed in the schema; changing embedding models to a
different size requires a migration.

Not yet modelled: `CharacterVersion`, visual style/era entities, tags — add when a consumer exists.

## Security posture (local-first, no auth yet)

URL allow-listing for YouTube, storage keys sanitised and resolved under the storage root, streaming uploads with a
size cap, parameterised SQL via SQLAlchemy, no shell invocation of user input, keys server-side only, CORS limited
to configured origins. There is **no authentication**: do not expose the API beyond localhost.
