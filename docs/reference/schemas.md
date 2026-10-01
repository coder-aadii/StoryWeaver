# Schema Reference

> Index of the machine-readable contracts and where each is defined.

## Status

Implemented.

| Contract | Source of truth | Derived copies |
| --- | --- | --- |
| Database tables | [`apps/api/app/models/domain.py`](../../apps/api/app/models/domain.py), migration in `apps/api/alembic/versions/` | Documented in [database schema](../data/database-schema.md) |
| Status enums | [`apps/api/app/models/enums.py`](../../apps/api/app/models/enums.py) | [data model](../data/data-model.md) |
| API request/response | [`apps/api/app/schemas/resources.py`](../../apps/api/app/schemas/resources.py) | OpenAPI at `GET /openapi.json`, UI at `/docs` |
| `SceneSpec`, `Timeline` | [`apps/api/app/schemas/scene.py`](../../apps/api/app/schemas/scene.py) | `packages/schemas/{scene,timeline}.schema.json` (generated), zod mirror in `packages/video/src/types.ts` (**hand-maintained**) |
| `NormalizedSource`, `TranscriptSegment` | [`apps/api/app/schemas/source.py`](../../apps/api/app/schemas/source.py) | `packages/schemas/normalized-source.schema.json` |

Regenerate JSON Schema with `make schemas`. When changing the timeline shape, update the Pydantic model, regenerate, update the zod mirror and `packages/video/sample/timeline.json`, and run both test suites ([adding a Remotion composition](../development/adding-a-remotion-composition.md)).

Nothing validates the zod mirror against the generated JSON Schema automatically — drift is possible and already exists: `camera` is required in zod but defaults in Python, and `camera.shot` is a free string in zod but a fixed set in Python ([KI-7](status.md#known-issues-and-limitations)). Planned: a contract test.

Target (not implemented): the richer canonical scene document in [scene data model](../data/scene-data-model.md).
