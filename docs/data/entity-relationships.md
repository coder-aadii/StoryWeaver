# Entity Relationships

> How the 17 tables relate; the canonical database/domain diagram.

## Status

**Implemented** (diagram reflects `apps/api/app/models/domain.py`).

## Diagram

```mermaid
erDiagram
    channels |o--o{ source_videos : "channel_id (SET NULL)"
    source_videos ||--o{ transcripts : "source_video_id"
    transcripts ||--o{ transcript_chunks : "transcript_id"
    collections ||--o{ collection_videos : ""
    source_videos ||--o{ collection_videos : ""
    projects ||--o{ project_sources : ""
    source_videos ||--o{ project_sources : ""
    projects ||--o{ scripts : "project_id"
    scripts ||--o{ script_versions : "script_id"
    projects ||--o{ scenes : "project_id"
    scripts |o--o{ scenes : "script_id (SET NULL)"
    scenes ||--o{ scene_versions : "scene_id"
    projects ||--o{ characters : "project_id"
    projects ||--o{ locations : "project_id"
    projects ||--o{ assets : "project_id"
    scenes |o--o{ assets : "scene_id (SET NULL)"
    projects ||--o{ renders : "project_id"
    assets |o--o{ renders : "output_asset_id (SET NULL)"

    channels {
        uuid id PK
        string platform
        string external_id
        string status
    }
    source_videos {
        uuid id PK
        string external_id
        string status
    }
    transcripts {
        uuid id PK
        int version
        string status
    }
    transcript_chunks {
        uuid id PK
        int chunk_index
        vector embedding
    }
    topics {
        uuid id PK
        string slug
    }
    collections {
        uuid id PK
        string name
    }
    projects {
        uuid id PK
        string status
    }
    scenes {
        uuid id PK
        int sequence
        string status
    }
    assets {
        uuid id PK
        string type
        string status
        string storage_key
    }
    renders {
        uuid id PK
        string status
        jsonb timeline
    }
```

Attributes are shown for a subset of tables; the complete columns are in [database-schema](database-schema.md). `channel_id` on `source_videos` is nullable, hence the optional (`|o`) end of the first relationship. `topics` has no relationships yet: a topic ↔ video/chunk link is *Planned — not implemented* (*Decision pending* on shape). `scripts`/`scenes` both hang off `projects`; `scenes.script_id` is optional so a scene can survive deletion of its script.

## Cardinality notes

- **Source reuse**: a `source_video` appears once (unique per platform+external id) and links to many projects through `project_sources` and many collections through `collection_videos`. See [source-data-model](source-data-model.md).
- **Versions**: parent → versions is 1:N, unique per `(parent, version)`; "current" version is not stored (derive as max version; *Decision pending* whether to add a pointer).
- **Deletion**: deleting a project cascades to scripts, scenes, characters, locations, assets, renders and join rows. Deleting a channel keeps its videos (`channel_id` → NULL). See [data-lifecycle](data-lifecycle.md).

## Related

[database-schema](database-schema.md) · [architecture/domain-architecture](../architecture/domain-architecture.md)
