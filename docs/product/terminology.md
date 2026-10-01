# Terminology

> Product-level vocabulary used across StoryWeaver documentation. Technical/code terms are in [reference/glossary](../reference/glossary.md).

## Status

**Implemented** (documentation). Terms marked *(planned)* name concepts that do not exist in code yet.

| Term | Meaning |
| --- | --- |
| **Source** | Any input knowledge: video, channel, playlist, transcript, file, later web/document. In code, a platform-neutral `NormalizedSource` ([source-data-model](../data/source-data-model.md)). |
| **Source video** | A stored video record (`source_videos`), unique per `(platform, external_id)`. |
| **Channel** | A platform channel record (`channels`) that groups source videos. |
| **Transcript** | Text of a source video with optional timed segments (`transcripts`: one `text` and a `segments` list). A `version` column exists per video, but versioning is a **Target** — the API cannot set it today ([KI-13](../reference/status.md#known-issues-and-limitations)). A raw-vs-cleaned split is **Decision pending**. |
| **Transcript chunk** | A timed slice of a transcript (~1200 chars by default) that carries an embedding (`transcript_chunks`). |
| **Embedding** | Vector (768 dims in the schema) used for semantic search in pgvector. |
| **Collection** | A user-defined group of source videos (e.g. "History"). |
| **Topic** | A named theme/classification; manual CRUD today, automatic extraction *(planned)*. |
| **Project** | One video-making effort; may use many sources; a source may feed many projects. |
| **Idea / story candidate** *(planned)* | A proposed story angle derived from source understanding. |
| **Story architecture** *(planned)* | Hook → Setup → Development → Conflict/Tension → Escalation → Climax → Resolution plan for one story. |
| **Script / script version** | The narration text and structure for a project; each revision is intended to be an immutable `script_versions` row (nothing enforces immutability yet; there is no API for versions). |
| **Storyboard** | Ordered list of scenes planned from the script. |
| **Scene** | One unit with narration, visual intent, camera and audio intent; own id, status and versions. |
| **Scene intent** *(planned)* | What a scene must communicate in the story ("what does the viewer need to see now?"). Distinct from the image prompt, the generated asset and the timeline shot — canonical definition in [storyboard-system](../domains/storyboard-system.md). |
| **Image prompt** | The text sent to an `ImageGenerator` for a scene (`SceneSpec.image_prompt`); derived from scene intent plus the bibles. |
| **Shot** *(planned)* | A timed use of an asset on the timeline; one scene may have several shots and one image may serve several shots. **Not an entity in code today.** Not to be confused with `CameraSpec.shot`. |
| **`CameraSpec.shot`** | The *framing type* of a scene's camera (`wide`, `medium`, `close_up`, …) in `SceneSpec`; a field, not the Shot entity above. |
| **SceneSpec** | Pydantic model for what AI decides about a scene ([scene-data-model](../data/scene-data-model.md)). |
| **Timeline** | Deterministic JSON with resolved start/duration per scene; the renderer's only input ([timeline-specification](../media/timeline-specification.md)). |
| **Character bible** *(planned)* | Structured identity of recurring characters used to keep them consistent. |
| **Visual bible** *(planned)* | Global style rules (palette, line, lighting, camera language, negative prompts, references). |
| **Asset** | A file-backed artefact (image, voice, music, sfx, subtitle, render, …) with status; bytes live on disk, not in Postgres ([asset-data-model](../data/asset-data-model.md)). |
| **Render** | A record of one timeline → MP4 job. |
| **Camera motion** | Deterministic zoom/pan/tilt applied to a still image ([camera-motion](../media/camera-motion.md)). |
| **Provider** | Interchangeable backend for a capability (LLM, embedding, image, voice, transcription, extractor). |
| **Source Provider** | The ingestion implementation for one kind of source (YouTube/yt-dlp today; a transcript upload is another). It produces a `NormalizedSource`; platform specifics must not leak past it — chain in [source-library](../domains/source-library.md). |
| **Source fingerprint** *(planned)* | An identifier (e.g. content hash) used to detect duplicate or near-duplicate sources beyond `(platform, external_id)`. |
| **Source usage** *(planned)* | A record of which sources and ideas a project used, so ideas can be reused or avoided. Not modelled today ([KI-22](../reference/status.md#known-issues-and-limitations)). |
| **Factual grounding** | Keeping a story consistent with the facts, events and concepts found in the source material. |
| **Narrative originality** | The story's own structure, hook, pacing, framing, narration, scene order and emphasis, as opposed to the source's wording and structure. A product goal measured by similarity checks *(planned)*, not a guarantee. |
| **Staged gating** *(planned)* | Running cheap analysis first and expensive generation (images, voice, render) only after the user approves the story — see [ai-cost-strategy](../ai/ai-cost-strategy.md). |
| **Artifact dependency** *(planned)* | The explicit relation "artifact B was derived from artifact A", used to invalidate or preserve downstream artifacts when A changes — model in [workflow-overview](../workflows/workflow-overview.md). |
| **Workflow** | A long-running, ideally idempotent operation; `LocalRunner` today, Temporal *(future)*. |
| **QA** *(planned)* | Automated checks on assets and rendered output. |
| **Local-first** | Runs on the user's machine with no mandatory cloud dependency. |
| **AI decides content / code decides timing** | The core responsibility split ([ADR-004](../decisions/ADR-004-ai-vs-deterministic-responsibilities.md)). |

## Status words used in these docs

- **Implemented** — exists in code and is exercised by tests or verified run.
- **Partially implemented** — some parts exist; the doc says which.
- **Planned — not implemented** — designed, no code.
- **Future / Deferred** — not scheduled; "Deferred until required by the production workflow".
- **Decision pending** — undecided.
- **Target Architecture** — intended design, not current behaviour.
