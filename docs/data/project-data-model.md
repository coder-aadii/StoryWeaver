# Project Data Model

> The project aggregate: what a project owns and how it links to sources.

## Status

**Partially implemented.** Tables and CRUD for projects exist. `ProjectSource` has no API. Pipeline stages that would drive `ProjectStatus` are *Planned — not implemented*.

## Aggregate

```text
Project ─┬─ ProjectSource ─▶ SourceVideo   (many-to-many, role)
         ├─ Script ── ScriptVersion
         ├─ Scene  ── SceneVersion
         ├─ Character, Location
         ├─ Asset
         └─ Render
```

Everything under a project cascades on project deletion. Sources are **never** copied into a project — only referenced — so one source can feed many projects ([ADR-005](../decisions/ADR-005-postgres-pgvector.md) for why PostgreSQL is the single source of truth).

## Project fields

| Field | Type | Meaning |
| --- | --- | --- |
| `title` | str ≤ 512 | required |
| `description` | text? | |
| `status` | `ProjectStatus` | default `draft`; coarse stage marker |
| `settings` | JSONB dict | free-form per-project config (target length, style, provider choices…). **No schema and no defined keys** — *Decision pending*; also a candidate home for approval-gate state ([domains/project-system](../domains/project-system.md)) and a Visual Bible ([story-data-model](story-data-model.md#visual-bible-target-and-where-it-lives-today)) |
| `error` | text? | last project-level failure |

## Status vs. granular status

`ProjectStatus` (draft → analyzing → scripting → storyboarding → generating → rendering → qa → completed | failed) is a coarse indicator. Failures of single scenes/assets/renders are stored on those rows (`scenes.status/error`, `assets.status/error`, `renders.status/error`) so one failure does not fail the project (design principle: [architecture/workflow-architecture](../architecture/workflow-architecture.md)). Today nothing automatically advances `status`.

## ProjectSource

PK `(project_id, source_video_id)`, `role` default `primary` (other roles *Decision pending*). Table only; no endpoint, no UI.

## Current limitations

- No project-level ownership/user (no auth).
- No archive/soft-delete flag; DELETE is hard and cascades ([data-lifecycle](data-lifecycle.md)).

See [domains/project-system](../domains/project-system.md), [api/resources/projects](../api/resources/projects.md).

## Gaps vs. target

Per-project pipeline stage state is only the coarse `status`; approval-gate state (candidate chosen, storyboard approved) has no defined home — *Decision pending* in [domains/project-system](../domains/project-system.md). Dependency tracking, story-side gaps and source-usage gaps are described once, in [story-data-model](story-data-model.md#target-model-gaps-verified-absent-from-the-schema), [source-data-model](source-data-model.md#target-model-gaps-verified-absent-from-the-schema) and [asset-data-model](asset-data-model.md#artifact-versions-and-dependencies-target).
