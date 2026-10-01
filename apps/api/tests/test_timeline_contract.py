"""Contract between the Pydantic models and their TypeScript (zod) mirror.

The canonical samples in ``packages/schemas/samples`` are generated from Pydantic by
``scripts/export_schemas.py`` (``make schemas``) and consumed by this test and by
``packages/video/src/contract.test.ts``. Changing a model on one side only fails one of them.
"""

import importlib.util
import json
import re
import typing
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.scene import CameraMovement, SceneSpec, ShotType, Timeline

REPO = Path(__file__).resolve().parents[3]
SAMPLES = REPO / "packages" / "schemas" / "samples"
TYPES_TS = REPO / "packages" / "video" / "src" / "types.ts"


def _load_exporter() -> Any:
    spec = importlib.util.spec_from_file_location(
        "export_schemas", REPO / "scripts" / "export_schemas.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXPORTER = _load_exporter()
EXPECTED = EXPORTER.build_samples()


def _read(name: str) -> Any:
    return json.loads((SAMPLES / name).read_text())


def _names(prefix: str) -> list[str]:
    return sorted(n for n in EXPECTED if n.startswith(prefix))


def test_committed_samples_match_pydantic() -> None:
    """Fails with 'run make schemas' if models changed without regenerating the samples."""
    assert sorted(p.name for p in SAMPLES.glob("*.json")) == sorted(EXPECTED), "run `make schemas`"
    for name, doc in EXPECTED.items():
        assert _read(name) == doc, f"{name} is stale; run `make schemas`"


def test_json_schemas_are_current() -> None:
    for name, model in EXPORTER.SCHEMAS.items():
        committed = json.loads((REPO / "packages" / "schemas" / f"{name}.schema.json").read_text())
        assert committed == model.model_json_schema(), (
            f"{name}.schema.json is stale; run `make schemas`"
        )


@pytest.mark.parametrize("name", _names("timeline.invalid."))
def test_invalid_timeline_samples_fail_in_pydantic(name: str) -> None:
    with pytest.raises(ValidationError):
        Timeline.model_validate(_read(name))


@pytest.mark.parametrize("name", _names("scene-spec.invalid."))
def test_invalid_scene_spec_samples_fail_in_pydantic(name: str) -> None:
    with pytest.raises(ValidationError):
        SceneSpec.model_validate(_read(name))


def test_valid_timeline_samples_round_trip() -> None:
    full = _read("timeline.valid.full.json")
    assert Timeline.model_validate(full).model_dump(mode="json") == full
    minimal = Timeline.model_validate(_read("timeline.valid.minimal.input.json"))
    assert minimal.model_dump(mode="json") == _read("timeline.valid.minimal.expected.json")


def test_valid_scene_spec_samples_round_trip() -> None:
    full = _read("scene-spec.valid.full.json")
    assert SceneSpec.model_validate(full).model_dump(mode="json") == full
    minimal = SceneSpec.model_validate(_read("scene-spec.valid.minimal.input.json"))
    assert minimal.model_dump(mode="json") == _read("scene-spec.valid.minimal.expected.json")


def _zod_enum(const_name: str) -> list[str]:
    source = TYPES_TS.read_text()
    match = re.search(rf"export const {const_name} = z\.enum\(\[(.*?)\]\)", source, re.S)
    assert match, f"{const_name} not found in types.ts"
    return re.findall(r'"([^"]+)"', match.group(1))


def test_zod_enums_match_pydantic_literals() -> None:
    assert _zod_enum("cameraMovement") == list(typing.get_args(CameraMovement))
    assert _zod_enum("cameraShot") == list(typing.get_args(ShotType))
