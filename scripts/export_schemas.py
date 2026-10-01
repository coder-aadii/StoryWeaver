"""Export Pydantic contracts into packages/schemas (consumed by the video package).

Writes, deterministically:
  * ``<name>.schema.json``      JSON Schema of each Pydantic model
  * ``samples/*.json``          canonical valid / invalid documents used by BOTH test suites
                                (apps/api/tests/test_timeline_contract.py and
                                packages/video/src/contract.test.ts), so a contract change made on
                                only one side (Pydantic or the zod mirror) fails ``make test``.

Run: ``make schemas``  (cd apps/api && uv run python ../../scripts/export_schemas.py)
"""

import json
from pathlib import Path
from typing import Any

from app.schemas.scene import CameraSpec, SceneSpec, Timeline, TimelineScene
from app.schemas.source import NormalizedSource

OUT = Path(__file__).resolve().parents[1] / "packages" / "schemas"
SAMPLES = OUT / "samples"

SCHEMAS = {"scene": SceneSpec, "timeline": Timeline, "normalized-source": NormalizedSource}


def build_samples() -> dict[str, Any]:
    """Return {filename: JSON-serialisable document}. Pure and deterministic."""
    full = Timeline(
        version=1,
        fps=30,
        width=1280,
        height=720,
        scenes=[
            TimelineScene(
                scene_id="scene_001",
                start=0,
                duration=2.5,
                narration="Long ago, the ice reached the sea.",
                subtitle="Long ago, the ice reached the sea.",
                image_src="images/scene_001.png",
                audio_src="audio/scene_001.wav",
                camera=CameraSpec(shot="wide", movement="slow_zoom_in"),
            ),
            TimelineScene(
                scene_id="scene_002",
                start=2.5,
                duration=2.0,
                camera=CameraSpec(shot="close_up", movement="pan_right"),
            ),
        ],
    )
    minimal_timeline_in: dict[str, Any] = {
        "scenes": [{"scene_id": "scene_001", "start": 0, "duration": 2}]
    }
    minimal_timeline_expected = Timeline.model_validate(minimal_timeline_in).model_dump(mode="json")

    scene_full = SceneSpec(
        scene_id="scene_001",
        sequence=1,
        narration="A small band walked south.",
        duration=3.2,
        visual_intent="Wide shot of a small group on a glacier",
        characters=["elder"],
        locations=["glacier"],
        objects=["torch"],
        action="walking",
        emotion="resolve",
        camera=CameraSpec(shot="wide", movement="pan_left"),
        image_prompt="storybook illustration, glacier, small group walking",
        negative_prompt="photo, text",
        voice="narrator",
        music="calm",
        sfx=["wind"],
        subtitle="A small band walked south.",
    )
    scene_min_in: dict[str, Any] = {"scene_id": "scene_001", "sequence": 1, "narration": "Hello."}
    scene_min_expected = SceneSpec.model_validate(scene_min_in).model_dump(mode="json")

    ok_scene = {"scene_id": "s", "start": 0, "duration": 1}

    def tl(**overrides: Any) -> dict[str, Any]:
        return {"scenes": [{**ok_scene, **overrides}]}

    return {
        # --- Timeline (shared with zod) -------------------------------------------------
        "timeline.valid.full.json": full.model_dump(mode="json"),
        "timeline.valid.minimal.input.json": minimal_timeline_in,
        "timeline.valid.minimal.expected.json": minimal_timeline_expected,
        "timeline.invalid.missing-scenes.json": {"version": 1},
        "timeline.invalid.scene-id-not-string.json": tl(scene_id=5),
        "timeline.invalid.negative-start.json": tl(start=-0.1),
        "timeline.invalid.zero-duration.json": tl(duration=0),
        "timeline.invalid.unknown-movement.json": tl(camera={"shot": "wide", "movement": "spin"}),
        "timeline.invalid.unknown-shot.json": tl(
            camera={"shot": "dutch_angle", "movement": "static"}
        ),
        "timeline.invalid.fractional-fps.json": {**tl(), "fps": 29.97},
        "timeline.invalid.fractional-version.json": {**tl(), "version": 1.5},
        # --- SceneSpec (Python-only today: no zod mirror exists yet) ---------------------
        "scene-spec.valid.full.json": scene_full.model_dump(mode="json"),
        "scene-spec.valid.minimal.input.json": scene_min_in,
        "scene-spec.valid.minimal.expected.json": scene_min_expected,
        "scene-spec.invalid.sequence-zero.json": {**scene_min_in, "sequence": 0},
        "scene-spec.invalid.zero-duration.json": {**scene_min_in, "duration": 0},
        "scene-spec.invalid.unknown-movement.json": {
            **scene_min_in,
            "camera": {"shot": "wide", "movement": "spin"},
        },
        "scene-spec.invalid.missing-narration.json": {"scene_id": "scene_001", "sequence": 1},
    }


def dumps(doc: Any) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    SAMPLES.mkdir(parents=True, exist_ok=True)
    for name, model in SCHEMAS.items():
        (OUT / f"{name}.schema.json").write_text(dumps(model.model_json_schema()))
        print("wrote", name)
    samples = build_samples()
    for stale in SAMPLES.glob("*.json"):
        if stale.name not in samples:
            stale.unlink()
            print("removed stale", stale.name)
    for filename, doc in samples.items():
        (SAMPLES / filename).write_text(dumps(doc))
    print(f"wrote {len(samples)} samples")


if __name__ == "__main__":
    main()
