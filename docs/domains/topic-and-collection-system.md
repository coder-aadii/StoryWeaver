# Topic and Collection System

> Organising the source library with topics (what a source is about) and collections (user-curated groups).

## Status

**Partially implemented.** Tables and CRUD for `topics` and `collections` exist; the join table `collection_videos` exists but has **no API endpoint**; automatic topic classification, tags and UI management are **Planned — not implemented**.

## Purpose

Make a large library navigable and usable as a scope for search and idea discovery.

## Problem being solved

Without grouping, finding "my history sources" or "unused ideas in a theme" requires manual searching.

## Inputs

User actions (create collection, add video), classifier output (topic labels).

## Outputs

Topic/collection records and membership.

## Entities

| Entity | Table | Notes |
| --- | --- | --- |
| Topic | `topics` | unique `name`, unique `slug` (slug pattern enforced at API: lowercase-hyphen) |
| Collection | `collections` | unique `name`, `description` |
| CollectionVideo | `collection_videos` | composite PK `(collection_id, source_video_id)`, cascade on delete |

No source↔topic link table exists yet (Decision pending — needed before classification).

## Workflow

Manual today (API only): create a collection; membership can only be inserted at DB level. Target: user adds videos in UI; classifier suggests topics, user confirms; collections feed search scope and idea-coverage queries.

## Business rules

- A video can be in many collections; a collection never owns the video.
- Deleting a collection removes memberships only.
- Topic slugs are stable identifiers; names may change.

## AI responsibilities

Classify sources into topics (cheap local model, see [model routing](../ai/model-routing.md)); suggest collection groupings.

## Deterministic responsibilities

Uniqueness, membership integrity, counts, filtering.

## Current implementation

`GET/POST/PATCH/DELETE /api/v1/topics`, `/collections` ([topics](../api/resources/topics.md), [collections](../api/resources/collections.md)); web pages `/topics` and `/collections` are read-only lists.

## Planned implementation

Membership endpoints, source↔topic relation, classification workflow, tags, "unused idea" tracking tied to [projects](project-system.md).

## Edge cases

Duplicate names differing by case; merging topics; hierarchical topics (not modelled).

## Open questions

Hierarchy vs flat topics; free-form tags vs topics; how "used/unused" is derived (from `project_sources`?).
