# Story Data Model

> How scripts, versions, characters and locations are stored, and what the future story structure will add.

## Status

**Partially implemented.** `scripts`, `script_versions`, `characters`, `locations` tables exist; scripts have a basic CRUD API; versions, characters and locations have **no** API. Story architecture storage (candidates, arcs, beats) is **Planned — not implemented** and has no tables.

## Implemented

### Script / ScriptVersion
- `Script(project_id, title)` — a named script slot in a project.
- `ScriptVersion(script_id, version, content JSONB, prompt_version?, provider?, model?)` — intended to be immutable, but **nothing enforces it** (no constraint, no API for versions); unique per `(script_id, version)`; unique per `(script_id, version)`. Recording `prompt_version`/`provider`/`model` supports reproducibility and cost analysis.
- The JSON shape of `content` is **not defined** yet — *Decision pending*; it will carry story-structure beats and scene intents ([domains/script-generation](../domains/script-generation.md)).

### Characters and locations
`Character` / `Location`: `(project_id, name)` unique, `description`, `attributes` JSONB. **The `attributes` keys are undefined**: nothing validates them and no schema (Pydantic or otherwise) lists the intended keys (age, clothing, build, hair, accessories, style…). Defining a `CharacterAttributes` model is *Decision pending*; until then any consumer must tolerate arbitrary or missing keys.

`SceneSpec.characters` / `.locations` are plain `list[str]`. That they hold the character's `name` is a **convention, not an enforced relationship**: there is no FK from scenes to characters, a rename silently breaks references, and nothing checks that a referenced name exists — *Decision pending* (name-based convention vs. IDs vs. a link table). Design: [domains/character-system](../domains/character-system.md), [domains/visual-system](../domains/visual-system.md). `Character`/`Location` have **no API** (tables only; see [api/resources/characters](../api/resources/characters.md)).

## Target (not implemented)

```text
Source understanding → StoryCandidate(s) → chosen StoryArchitecture
  Hook → Setup → Development → Conflict → Escalation → Climax → Resolution
  → Script (ScriptVersion.content) → SceneSpec[]
```

Candidate and architecture storage — see [options below](#story-candidate-and-source-analysis-storage-options-decision-pending) ([domains/story-generation](../domains/story-generation.md)).

## Deferred

- `CharacterVersion` (appearance history, reference-image sets): *Deferred until required by the production workflow*. Today edits to a character overwrite the row.
- Visual style / era / object entities; global "visual bible" row: only expressible today via `projects.settings` or `characters.attributes`.
- Reference images attach as `Asset(type=reference)`; no explicit link table to characters ([asset-data-model](asset-data-model.md)).

See [scene-data-model](scene-data-model.md).

## Story-candidate and source-analysis storage options (Decision pending)

**What must be stored (Target).** *Source analysis* (facts, events, entities, themes, conflicts, causal chains, turning points, hooks) and *story candidates* (title, premise, hook, central question, protagonist/subject, conflict, stakes, major beats, climax, resolution, source grounding with chunk references, estimated duration, target audience, tone, originality/similarity signals, **status: proposed / selected / rejected**). A candidate must be individually selectable, because one source can yield several independent stories, one story, or none ([domains/story-generation](../domains/story-generation.md)). Both are cacheable: re-analysing an unchanged source with the same prompt/model should not pay again ([ai/ai-cost-strategy](../ai/ai-cost-strategy.md)). **No tables, columns or caching exist today** ([KI-22](../reference/status.md#known-issues-and-limitations)).

| Option | Shape | Pros | Cons |
| --- | --- | --- | --- |
| A. JSONB inside existing rows | `Project.settings` / `ScriptVersion.content` hold analysis and candidates | No migration; fastest to start | Not queryable per candidate; no per-candidate status/versioning; analysis cannot be shared across projects; `settings` has no schema; hard to cache by `(transcript, prompt_version, model)` |
| B. Generic artifact table | one `artifacts` table: `id`, `project_id?`, `kind` (analysis / candidate / …), `parent_id?`, `version`, `status`, `payload` JSONB, `provider`, `model`, `prompt_version`, `input_hash` | One mechanism for analysis, candidates, bibles, and dependency edges; natural cache key (`input_hash`); easy to add kinds | Weakly typed payloads (validate with Pydantic per `kind`); generic queries are less self-documenting |
| C. Dedicated tables | `source_analyses`, `story_candidates` (+ `candidate_sources`) | Strong typing, FK integrity, per-field indexes, clear queries | More migrations; schema churn while the candidate shape is still being designed |

No option is chosen. Whichever is picked must record provider/model/prompt version and an input hash (cacheability), allow a candidate to cite source chunks (grounding) and be rejected or selected without deleting it, and fit the approval-gate state described in [domains/project-system](../domains/project-system.md). Originality/similarity signals are stored per the direction in [embeddings-and-vector-search](embeddings-and-vector-search.md#originality-and-similarity-data-direction).

## Visual Bible (target) and where it lives today

**Target.** A per-project (optionally reusable across projects) specification every scene prompt must consult: global art style, illustration style, line quality, palette/color language, lighting, environment language, camera language, aspect ratio, composition rules, reference images, negative prompts, consistency rules ([domains/visual-system](../domains/visual-system.md), [ai/consistency-strategy](../ai/consistency-strategy.md)). Scenes should *reference* it rather than re-describe it.

**Today.** No Visual Bible entity exists. The only places it could be put are `projects.settings` (free-form, no defined keys) and `characters.attributes`/`locations.attributes` (undefined keys). Nothing reads either for prompting. `SceneSpec.negative_prompt` is a per-scene string with no link to a project-level bible. Reference images would be `Asset(type=reference)` with no link to characters or to a bible ([asset-data-model](asset-data-model.md)).

**Options (Decision pending).**

| Option | Shape | Trade-off |
| --- | --- | --- |
| 1. `projects.settings.visual_bible` JSONB, validated by a Pydantic `VisualBible` model | no migration; one bible per project | no history; hard to reuse across projects |
| 2. `visual_bibles` table (`id`, `project_id?`, `name`, `version`, `data` JSONB, reference asset ids) | versioned, reusable ("house style"), can be pinned by scenes | needs a migration, a scene→bible-version link, and an invalidation rule when it changes |
| 3. Rows in the generic `artifacts` table (option B above) | same mechanism as analysis/candidates and dependency edges | weaker typing |

A change to a Visual Bible (or a character) should mark dependent images *stale* rather than silently diverge — see [artifact versions and dependencies](asset-data-model.md#artifact-versions-and-dependencies-target). `CharacterVersion` remains **Deferred until required by the production workflow**.

## Target-model gaps (verified absent from the schema)

Story-side gaps; each is described once, in the section named. Source-side gaps are in [source-data-model](source-data-model.md#target-model-gaps-verified-absent-from-the-schema); asset/version/dependency gaps in [asset-data-model](asset-data-model.md#artifact-versions-and-dependencies-target).

| Gap | Where described |
| --- | --- |
| Story candidates, source-analysis artifacts, their caching | [Storage options](#story-candidate-and-source-analysis-storage-options-decision-pending) |
| Visual Bible entity; `characters.attributes` keys undefined; name-based character references | [Visual Bible](#visual-bible-target-and-where-it-lives-today), [Characters and locations](#characters-and-locations) |
| Approval-gate state (candidate chosen, storyboard approved) | Decision pending — [domains/project-system](../domains/project-system.md) |
| Artifact dependency tracking / invalidation | [asset-data-model](asset-data-model.md#artifact-versions-and-dependencies-target) |
| Script v1/v2 ✔ (`script_versions`), Scene 12 v1/v2 ✔ (`scene_versions`), Image of scene 12 v1/v2 ✘ | [asset-data-model](asset-data-model.md#artifact-versions-and-dependencies-target) |
