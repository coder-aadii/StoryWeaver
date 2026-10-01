# Requirements

> Functional and non-functional requirements, each tagged with its implementation state.

## Status

**Partially implemented.** Requirement IDs are stable references for roadmap and tests. The "State" column is the truth today.

State legend: **Implemented** · **Partial** · **Planned** (not implemented) · **Future** (not scheduled).

## Functional requirements

### Sources and knowledge

| ID | Requirement | State | Notes |
| --- | --- | --- | --- |
| FR-S1 | Accept a YouTube video URL and validate it | **Implemented** (P1) | `POST /sources/from-url`: YouTube **video** URLs only (watch / youtu.be / shorts / embed); channel and playlist URLs → `422 unsupported_kind`; foreign hosts, schemes and look-alike domains → `422 invalid_source`; a missing optional yt-dlp → `409` with an install hint before anything is created. `POST /channels` validates a channel URL on create. Metadata and captions verified live once (2026-10-01); other paths by recorded fixtures ([verification record](../reference/status.md#verification-record)) |
| FR-S2 | Scan a channel/playlist and report video count before import | Partial | `list_videos` exists in the extractor (unused); the scan/confirm flow and the API are Planned (P11) |
| FR-S3 | Import N of M videos via a workflow | Planned | See [channel-ingestion](../domains/channel-ingestion.md) |
| FR-S4 | Store metadata and transcripts with timestamps | **Implemented** (P1) | Metadata on `source_videos`; transcripts versioned with one `is_current`; the raw file is stored as received (`raw_storage_key`, sha256) and the cleaned `text` + timestamped `segments` in the database; plain text has `null` times. Verified live once for manual captions ([verification record](../reference/status.md#verification-record)) |
| FR-S5 | Chunk and embed transcripts into pgvector | Partial | Chunking is implemented (1,200 characters, timing preserved, written with the transcript version); embedding generation is Planned (P11) — `embedding` stays NULL |
| FR-S6 | Semantic search / RAG across sources | Planned | **Keyword search is implemented** (`GET /sources/search`, Postgres full-text, ranked, highlighted snippets, timestamps); semantic/hybrid search and RAG are Planned (P11) |
| FR-S7 | Topics, collections, tags | Partial | Topic/Collection CRUD; membership endpoints, tags, auto-classification Planned/Deferred |
| FR-S8 | Accept TXT/SRT/VTT, local audio/video | Partial | **TXT/SRT/VTT** upload or paste is implemented (≤ 5 MB, UTF-8) and YouTube `json3`/`vtt` captions are parsed; local audio/video and other documents are Planned |
| FR-S9 | Detect duplicate sources | Partial | **Exact** duplicates are detected: unique `(platform, external_id)` (any YouTube URL form maps to one source) and an exact content fingerprint across formats and platforms. Near-duplicate / similarity detection is Planned (P12) |
| FR-S10 | Incremental channel sync: discover only videos not yet imported; idempotent, resumable, tolerate partial imports and retry failed items | Planned | No sync cursor or `last_synced` field exists ([KI-23](../reference/status.md#known-issues-and-limitations)). Channel identity must come from extractor output, not the URL fragment ([KI-24](../reference/status.md#known-issues-and-limitations)). See [channel-sync-workflow](../workflows/channel-sync-workflow.md) |
| FR-S11 | Build the library without downloading media: store URL, metadata, transcript, timestamps, chunks, embeddings; media download is an optional future capability when a workflow needs it | **Implemented** (P1) | Only a caption file is fetched (https, `youtube.com`/`googlevideo.com`, size-capped) and `skip_download` is forced; tests assert only the raw caption file lands in storage. `thumbnail_url` is stored as a remote URL, never fetched. Embeddings are Planned. See [source-library](../domains/source-library.md) |
| FR-S12 | Track which sources and ideas each project used (source usage) | Partial | **Project-level usage is implemented** (`PUT/DELETE/GET /projects/{id}/sources`, derived `usage_count`, `used`/`exclude_used` filters, delete blocked while used). Idea-level usage has no storage ([KI-22](../reference/status.md#known-issues-and-limitations)) |
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
| FR-P3 | Background workflows with persisted status/errors | Partial | `workflow_runs` (status, attempt, progress, `{code, message, retryable}` errors, one active run per kind and subject), `RunService`, `LocalRunner`, startup reconciliation and a manual retry endpoint exist for the Source Library ingestion; automatic retry/backoff, cancellation and the later pipeline stages are Planned (P2+) |
| FR-P7 | Model routing: different tasks use different models/providers (routine → cheap/local; analysis, story, script → stronger), considering quality, latency, cost, context window, structured-output support, availability, reliability | Planned — only per-task model *settings* exist; per-task provider routing is Decision pending ([model-routing](../ai/model-routing.md)) |
| FR-P8 | Cost tracking: record tokens, duration and cost per provider call | Planned — token counts are logged (not masked) but nothing persists them; no storage exists ([ai-cost-strategy](../ai/ai-cost-strategy.md)) |
| FR-P9 | Provider failure isolation: a failed provider call must not corrupt project state; calls are timeout-controlled, validated, retryable where appropriate and replaceable | Partial — status/error columns exist and provider failures surface as typed `ProviderError`s with a configurable timeout (`LLM_TIMEOUT_SECONDS`); no workflow persists failure state or retries yet |
| FR-P4 | Durable workflows (Temporal) | Future ([workflow-architecture](../architecture/workflow-architecture.md)) |
| FR-P5 | Object storage (S3/MinIO) | Future ([storage-architecture](../architecture/storage-architecture.md)) |
| FR-P6 | Authentication / multi-user | Future |

## Non-functional requirements

| ID | Requirement | State |
| --- | --- | --- |
| NFR-1 | Boot with zero optional providers configured | Implemented |
| NFR-2 | No model loaded or connection opened at import/startup | Implemented (lazy engine, lazy registry) |
| NFR-3 | Runs on ~16 GB RAM, no GPU | Implemented for foundation; unmeasured for AI/media workloads |
| NFR-4 | Provider keys server-side only and not logged | Partial — keys are read server-side and sent in headers; log redaction masks secret-named keys and scrubs secret-shaped values (including exception text) but is best-effort pattern matching |
| NFR-5 | Path traversal protection, upload size cap, streaming IO | Implemented in `LocalStorage` (tested); no route uses it and there is no upload endpoint ([KI-9](../reference/status.md#known-issues-and-limitations)) |
| NFR-6 | Idempotent, retryable operations | Planned (design intent; no operations yet) |
| NFR-7 | Structured logging with workflow/project/scene context | Partial (logging configured; few call sites) |
| NFR-8 | Observability of latency, tokens, durations, failure rates | Partial (some fields logged; no storage/metrics) |
| NFR-9 | Strict typing & lint gates | Implemented (pyright strict, ruff, tsc strict, ESLint) |
| NFR-10a | Timeline JSON is deterministic: same scenes → same timeline | Implemented and unit-tested (`build_timeline`) |
| NFR-10b | Render reproducibility: same timeline → same video | Planned / unverified — only one sample render has been produced and inspected; no test compares renders |
| NFR-11 | CI for lint and tests | Planned — no CI exists ([KI-10](../reference/status.md#known-issues-and-limitations)); checks run locally |

See [testing-strategy](../testing/testing-strategy.md) for how each is verified, and [status.md](../reference/status.md) for the subsystem view.
