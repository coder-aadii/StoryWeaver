# Use Cases

> Concrete scenarios StoryWeaver should support, with current feasibility.

## Status

**Planned.** Use cases are target scenarios. Today none can be completed end to end; the "Feasible today" line states exactly what can be done.

## UC-1 — Turn one 30-minute video into several stories

**Scenario:** A 30-minute documentary transcript contains three separable narrative opportunities.
**Expected:** The system identifies independent opportunities (themes, conflicts, causal chains, turning points) and offers however many story candidates it can justify (one, several, or **none** if the source yields no suitable story), each with its own arc and hook — *not* three 10-minute slices, and not a fixed number. See [story-generation](../domains/story-generation.md).
**Feasible today:** Only the first step. Since P1 you can add the source (YouTube video or transcript), have it stored, chunked and searchable by keyword, and link it to a project; no analysis, opportunity detection or story candidates exist (Planned).

## UC-2 — Build a library from a channel

**Scenario:** Enter `https://www.youtube.com/@SomeChannel/videos`, see the video count, import 25.
**Feasible today:** No. Channel and playlist URLs are recognised and refused with a clear message (`422 unsupported_kind`); a single video from a channel can be added, which records the channel (canonical id) and links the video to it. An extractor `list_videos` method exists but nothing calls it: no scan endpoint, no import workflow, no sync. See [channel-ingestion](../domains/channel-ingestion.md).

## UC-3 — Find prior ideas

**Scenario:** "Find all saved sources related to prehistoric human survival", "find unused ideas in History", "have I already generated a video around this concept?", "find relevant facts across 50 transcripts".
**Feasible today:** Partly. **Keyword search** over stored transcripts works (`GET /sources/search`, with timestamps, "hide sources already used" and per-source search), and project-level usage is tracked ("which projects used this source"). Semantic search, "similar ideas" and idea-level reuse do not: the schema supports embeddings (`transcript_chunks.embedding`, HNSW cosine index; nearest-neighbour query covered by a test) but none are generated. See [rag-strategy](../ai/rag-strategy.md), [embeddings-and-vector-search](../data/embeddings-and-vector-search.md).

## UC-4 — Produce a 10–15 minute illustrated, narrated video

**Scenario:** From an approved script to MP4 with camera motion, subtitles, music and SFX.
**Feasible today:** Only the last mile on sample data: `SceneSpec` → `build_timeline` → Remotion → MP4 (`make render-sample`). No image generation (mock only), no narration, no music/SFX, no project-level render workflow. See [media-overview](../media/media-overview.md).

## UC-5 — Regenerate one scene

**Scenario:** Scene 32's character looks wrong; regenerate only its image and re-render.
**Feasible today:** Data model supports independent scene/asset identity and statuses; no regeneration operation exists. See [retry-and-recovery](../workflows/retry-and-recovery.md).

## UC-6 — Run fully offline / at zero cost

**Scenario:** Use Ollama locally for analysis and scripting, ComfyUI locally for images, a local TTS engine, local rendering.
**Feasible today:** The app boots with no providers; Ollama adapter exists (its chat request shape is tested against a mock; the embedding adapter and all other LLM adapters are untested); ComfyUI is a stub; no local TTS. See [ADR-002](../decisions/ADR-002-local-first.md), [provider-selection](../ai/provider-selection.md).

## UC-7 — Mix cheap and strong models

**Scenario:** Cheap local model for classification/cleaning; stronger (possibly cloud) model for story architecture and script.
**Feasible today:** Settings expose per-task model names (`ANALYSIS_LLM_MODEL`, `STORY_LLM_MODEL`, `SCRIPT_LLM_MODEL`, `CLASSIFICATION_LLM_MODEL`) and `Settings.model_for(task)`; provider is currently selected only by `DEFAULT_LLM_PROVIDER` (per-task provider routing is **Decision pending**). See [model-routing](../ai/model-routing.md).

## UC-8 — Contribute a new provider or domain

**Scenario:** A developer adds a new LLM provider.
**Feasible today:** Yes — see [adding-a-provider](../development/adding-a-provider.md).

## Related

[user-flows](user-flows.md) · [requirements](requirements.md) · [feature-roadmap](feature-roadmap.md)

## UC-9 — Sync a previously imported channel

**Scenario:** Re-open an imported channel and press "Sync Channel"; only new videos are discovered and imported, failures can be retried, a partial import can resume.
**Feasible today:** No. No scan or sync endpoint, no sync cursor ([KI-23](../reference/status.md#known-issues-and-limitations)). See [channel-sync-workflow](../workflows/channel-sync-workflow.md).

## UC-10 — Approve a story before paying for assets

**Scenario:** Cheap analysis yields several story candidates; the user picks one; only then are the high-quality script, storyboard and expensive asset generation run.
**Feasible today:** No. See [ai-cost-strategy](../ai/ai-cost-strategy.md), [story-generation-workflow](../workflows/story-generation-workflow.md).

## UC-11 — Avoid repeating myself

**Scenario:** "Avoid ideas I have already used" and "is this script too close to a previous project or to its source?"
**Feasible today:** No. No used-idea or similarity storage ([KI-22](../reference/status.md#known-issues-and-limitations)); direction in [embeddings-and-vector-search](../data/embeddings-and-vector-search.md).

## UC-12 — Edit the production through the Studio

**Scenario:** Walk the ten stages, inspect intermediate outputs, regenerate at fine granularity, compare versions (Script v1/v2, Scene 12 v1/v2, Image Scene 12 v1/v2). See [user-flows F7](user-flows.md) and [studio](../frontend/studio.md).
**Feasible today:** No (placeholder Studio).
