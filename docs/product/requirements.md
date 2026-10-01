# Requirements

> Functional and non-functional requirements, each tagged with its implementation state.

## Status

**Partially implemented.** Requirement IDs are stable references for roadmap and tests. The "State" column is the truth today.

State legend: **Implemented** · **Partial** · **Planned** (not implemented) · **Future** (not scheduled).

## Functional requirements

### Sources and knowledge

| ID | Requirement | State | Notes |
| --- | --- | --- | --- |
| FR-S1 | Accept a YouTube video URL and validate it | Partial | `classify_youtube_url` validates, but it is applied only inside the extractor: `POST /sources` and `POST /channels` accept any URL string ([KI-12](../reference/status.md#known-issues-and-limitations)). Extraction needs optional yt-dlp, never run live, and returns metadata only ([KI-15](../reference/status.md#known-issues-and-limitations)) |
| FR-S2 | Scan a channel/playlist and report video count before import | Partial | `list_videos` exists in the extractor; scan/confirm flow is Planned |
| FR-S3 | Import N of M videos via a workflow | Planned | See [channel-ingestion](../domains/channel-ingestion.md) |
| FR-S4 | Store metadata and transcripts with timestamps | Partial | `Transcript` holds a single `text` plus `segments` JSONB; tables exist, ingestion workflow Planned. A raw-vs-cleaned split and where the raw file lives are **Decision pending**; transcript versioning is a Target ([KI-13](../reference/status.md#known-issues-and-limitations)). Uploaded transcripts without a remote origin are not currently representable ([KI-14](../reference/status.md#known-issues-and-limitations)) |
| FR-S5 | Chunk and embed transcripts into pgvector | Partial | `chunk_segments` + `vector(768)` column + HNSW index; embedding workflow Planned |
| FR-S6 | Semantic search / RAG across sources | Planned | |
| FR-S7 | Topics, collections, tags | Partial | Topic/Collection CRUD; membership endpoints, tags, auto-classification Planned/Deferred |
| FR-S8 | Accept TXT/SRT/VTT, local audio/video | Planned | |
| FR-S9 | Detect duplicate sources | Partial | Unique `(platform, external_id)`; content-level dedupe / source fingerprints Planned |
| FR-S10 | Incremental channel sync: discover only videos not yet imported; idempotent, resumable, tolerate partial imports and retry failed items | Planned | No sync cursor or `last_synced` field exists ([KI-23](../reference/status.md#known-issues-and-limitations)). Channel identity must come from extractor output, not the URL fragment ([KI-24](../reference/status.md#known-issues-and-limitations)). See [channel-sync-workflow](../workflows/channel-sync-workflow.md) |
| FR-S11 | Build the library without downloading media: store URL, metadata, transcript, timestamps, chunks, embeddings; media download is an optional future capability when a workflow needs it | Partial | Current extractor is metadata-only (`skip_download`); no thumbnail column ([KI-23](../reference/status.md#known-issues-and-limitations)). See [source-library](../domains/source-library.md) |
| FR-S12 | Track which sources and ideas each project used (source usage) | Planned | `project_sources` table exists with no endpoint; no storage for used ideas ([KI-22](../reference/status.md#known-issues-and-limitations)) |
| FR-S13 | Idea reuse: generate from one source, many sources, a topic or a collection, and avoid previously used ideas | Planned | Depends on FR-S12 and FR-S6 |

### Story and script

| ID | Requirement | State |
| --- | --- | --- |
| FR-G1 | Analyse a source into facts, themes, events, causal chains | Planned |
| FR-G2 | Propose multiple independent story candidates from one source | Planned |
| FR-G3 | Build a story architecture (Hook→…→Resolution) | Planned |
| FR-G4 | Write an original 10–15 min script, validated, versioned | Planned (tables Implemented) |
| FR-G5 | Flag or reject outputs that are too close to the source (similarity / originality check) | Planned |
| FR-G6 | Story candidates are presented to the user and **approved by the user before expensive downstream generation** (images, voice, render); an automatic selection heuristic may exist only as an opt-in shortcut | Planned — see [ai-cost-strategy](../ai/ai-cost-strategy.md), [project-system](../domains/project-system.md) |
| FR-G7 | Originality / similarity checks also compare against previous projects and previously used ideas | Planned — storage direction in [embeddings-and-vector-search](../data/embeddings-and-vector-search.md); no used-idea storage exists ([KI-22](../reference/status.md#known-issues-and-limitations)) |
| FR-G8 | Cache analysis artifacts (metadata, transcripts, chunks, embeddings, source analysis, topic extraction, story candidates, visual descriptions) so unchanged inputs are not re-paid for | Planned — no caching layer exists |
| FR-G9 | Prompts are versioned and the prompt version is recorded with generated artifacts | Planned — `script_versions.prompt_version` column exists; `packages/prompts` is empty |

### Visual and audio

| ID | Requirement | State |
| --- | --- | --- |
| FR-V1 | Storyboard as `SceneSpec` list | Schema Implemented; generation Planned |
| FR-V2 | Character bible, visual bible with consistency across scenes | Tables for characters/locations only; rest Planned |
| FR-V3 | Illustration generation per scene via `ImageGenerator` | Interface + mock Implemented; ComfyUI Planned |
| FR-V4 | Narration via `VoiceProvider` | Interface only; engine Planned |
| FR-V5 | Subtitles aligned to narration | Planned |
| FR-V6 | Music and SFX with ducking, loudness normalisation | Planned |

### Video and QA

| ID | Requirement | State |
| --- | --- | --- |
| FR-R1 | Deterministic timeline JSON from scenes | Implemented (timing and ordering). Resolving `image_src`/`audio_src` from assets is Planned ([KI-16](../reference/status.md#known-issues-and-limitations), [KI-17](../reference/status.md#known-issues-and-limitations)) |
| FR-R2 | Remotion composition from timeline | Implemented (`Basic`) |
| FR-R3 | Render timeline to MP4 | Implemented for the sample via CLI; project render workflow Planned |
| FR-R4 | Preview in the web app | Implemented (Remotion Player on `/studio`, sample data) |
| FR-Q1 | Automated QA (assets, timing, audio, subtitles, visuals) | Planned |
| FR-Q2 | Regenerate one scene/asset without rebuilding the project (per-scene regeneration) | Planned (identity/status fields Implemented; no regeneration operation) |
| FR-Q3 | Artifacts are versioned (Script v1/v2, Scene 12 v1/v2, Image Scene 12 v1/v2) with explicit dependencies, so an upstream change can invalidate or preserve downstream artifacts | Partial — `script_versions`/`scene_versions` tables only; asset versions and the dependency model are Decision pending ([workflow-overview](../workflows/workflow-overview.md)) |
| FR-Q4 | Studio lets the user inspect and modify intermediate outputs (source, transcript, facts, themes, candidates, script versions, scenes, bibles, image versions, narration, subtitles, timeline, QA results) | Planned — current Studio is a placeholder ([studio](../frontend/studio.md)) |

### Platform

| ID | Requirement | State |
| --- | --- | --- |
| FR-P1 | CRUD API for core resources under `/api/v1` | Implemented (10 groups) |
| FR-P2 | Health, readiness, provider status | Implemented |
| FR-P3 | Background workflows with persisted status/errors | Partial (`LocalRunner` only; no persisted workflow table; no route or service uses it — [KI-9](../reference/status.md#known-issues-and-limitations)) |
| FR-P7 | Model routing: different tasks use different models/providers (routine → cheap/local; analysis, story, script → stronger), considering quality, latency, cost, context window, structured-output support, availability, reliability | Planned — only per-task model *settings* exist; per-task provider routing is Decision pending ([model-routing](../ai/model-routing.md)) |
| FR-P8 | Cost tracking: record tokens, duration and cost per provider call | Planned — token counts are currently masked in logs ([KI-2](../reference/status.md#known-issues-and-limitations)); no storage exists ([ai-cost-strategy](../ai/ai-cost-strategy.md)) |
| FR-P9 | Provider failure isolation: a failed provider call must not corrupt project state; calls are timeout-controlled, validated, retryable where appropriate and replaceable | Partial — status/error columns and 120 s HTTP timeout exist; only `httpx.HTTPError` is wrapped, malformed responses escape ([KI-3](../reference/status.md#known-issues-and-limitations)) |
| FR-P4 | Durable workflows (Temporal) | Future ([workflow-architecture](../architecture/workflow-architecture.md)) |
| FR-P5 | Object storage (S3/MinIO) | Future ([storage-architecture](../architecture/storage-architecture.md)) |
| FR-P6 | Authentication / multi-user | Future |

## Non-functional requirements

| ID | Requirement | State |
| --- | --- | --- |
| NFR-1 | Boot with zero optional providers configured | Implemented |
| NFR-2 | No model loaded or connection opened at import/startup | Implemented (lazy engine, lazy registry) |
| NFR-3 | Runs on ~16 GB RAM, no GPU | Implemented for foundation; unmeasured for AI/media workloads |
| NFR-4 | Provider keys server-side only and not logged | Partial — keys are read server-side and sent in headers; log redaction is by key *name* only (substring match, which also masks `output_tokens`), and exception text is not scrubbed ([KI-2](../reference/status.md#known-issues-and-limitations)) |
| NFR-5 | Path traversal protection, upload size cap, streaming IO | Implemented in `LocalStorage` (tested); no route uses it and there is no upload endpoint ([KI-9](../reference/status.md#known-issues-and-limitations)) |
| NFR-6 | Idempotent, retryable operations | Planned (design intent; no operations yet) |
| NFR-7 | Structured logging with workflow/project/scene context | Partial (logging configured; few call sites) |
| NFR-8 | Observability of latency, tokens, durations, failure rates | Partial (some fields logged; no storage/metrics) |
| NFR-9 | Strict typing & lint gates | Implemented (pyright strict, ruff, tsc strict, ESLint) |
| NFR-10a | Timeline JSON is deterministic: same scenes → same timeline | Implemented and unit-tested (`build_timeline`) |
| NFR-10b | Render reproducibility: same timeline → same video | Planned / unverified — only one sample render has been produced and inspected; no test compares renders |
| NFR-11 | CI for lint and tests | Planned — no CI exists ([KI-10](../reference/status.md#known-issues-and-limitations)); checks run locally |

See [testing-strategy](../testing/testing-strategy.md) for how each is verified, and [status.md](../reference/status.md) for the subsystem view.
