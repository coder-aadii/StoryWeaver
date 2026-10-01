# Glossary

> Short definitions of StoryWeaver terms. Longer treatment lives in [terminology](../product/terminology.md).

## Status

Implemented (documentation).

| Term | Meaning |
| --- | --- |
| **Source** | Any input material: a video, channel, playlist, transcript, file. Modelled as `SourceVideo` (+ `Channel`). See [source library](../domains/source-library.md) |
| **NormalizedSource** | Platform-neutral extractor output ([schemas](schemas.md)) |
| **Transcript / chunk** | Timed text of a source / retrieval-sized slice with optional embedding |
| **Collection / Topic** | User grouping of videos / theme label |
| **Project** | One video-production effort, may use many sources |
| **Story candidate** | A proposed independent narrative extracted from source material (planned) |
| **Story architecture** | Hook → Setup → Development → Conflict → Escalation → Climax → Resolution |
| **Script / ScriptVersion** | Narration text document and its immutable versions |
| **Scene / SceneVersion** | Unit of the storyboard with independent identity and versions |
| **SceneSpec** | Pydantic model of a scene's AI-decided content |
| **Character Bible / Visual Bible** | *Planned.* Canonical definitions of characters and of the global look that scenes reference instead of re-describing |
| **Asset** | A stored file (image, voice, …) with metadata; bytes live outside Postgres |
| **Timeline** | Deterministic JSON of scenes with start/duration/assets/camera |
| **Camera motion** | Zoom/pan/tilt applied to a still image |
| **Render** | A record of a timeline → MP4 job |
| **Provider** | Swappable backend for LLM, embeddings, image, voice, or transcription |
| **Workflow / runner** | Long-running job and the thing that executes it |
| **Local-first** | Works with local models and storage; cloud is optional |
| **QA** | Automated checks on assets and renders (planned) |
| **Shot (timeline shot)** | *Planned.* A timed use of an asset within a scene (a scene may have several; a shot may reuse an image). **No `Shot` entity exists today** |
| **`CameraSpec.shot`** | *Implemented.* The framing type of a scene (`wide`, `close_up`, …) — a different thing from a timeline Shot; it is carried in data but does not affect rendering |
| **Scene intent / image prompt / asset / shot** | Four distinct concepts; see [storyboard system](../domains/storyboard-system.md) |
| **Factual grounding** | Staying faithful to the facts of the source material |
| **Narrative originality** | New structure, hook, pacing, framing, narration and scene order around those facts. Engineering/product goal; no legal conclusion is implied |
| **Staged gating** | Expensive generation (images, voice) happens only after earlier creative stages are approved by the user ([cost strategy](../ai/ai-cost-strategy.md)) |
| **Artifact dependency** | A relationship saying an artifact is derived from upstream artifacts, so changes can invalidate or preserve it ([model](../workflows/workflow-overview.md)). Not implemented |
| **Source usage** | Record of which sources/ideas a project used, to avoid reuse. Not modelled |
| **Source fingerprint** | Stable identifier(s) used to detect the same or near-duplicate source. Today only `unique(platform, external_id)` exists |
| **Source Provider** | The platform-specific implementation (e.g. YouTube via yt-dlp) that yields a `NormalizedSource`; domain code must not depend on it |
