"""Export Pydantic contracts as JSON Schema into packages/schemas (consumed by the video package).

Run: cd apps/api && uv run python ../../scripts/export_schemas.py
"""

import json
from pathlib import Path

from app.schemas.scene import SceneSpec, Timeline
from app.schemas.source import NormalizedSource

OUT = Path(__file__).resolve().parents[1] / "packages" / "schemas"
for name, model in {"scene": SceneSpec, "timeline": Timeline, "normalized-source": NormalizedSource}.items():
    (OUT / f"{name}.schema.json").write_text(json.dumps(model.model_json_schema(), indent=2) + "\n")
    print("wrote", name)
