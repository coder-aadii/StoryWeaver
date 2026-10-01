"""Scene / timeline contracts. The JSON shape is shared with the Remotion package."""

from typing import Literal

from pydantic import BaseModel, Field

ShotType = Literal["wide", "medium", "close_up", "extreme_close_up", "over_shoulder", "aerial"]
CameraMovement = Literal[
    "static", "slow_zoom_in", "slow_zoom_out", "pan_left", "pan_right", "tilt_up", "tilt_down"
]


class CameraSpec(BaseModel):
    shot: ShotType = "medium"
    movement: CameraMovement = "static"


class SceneSpec(BaseModel):
    """What the AI decides about a scene. Timing is later resolved by code."""

    scene_id: str
    sequence: int = Field(ge=1)
    narration: str
    duration: float | None = Field(default=None, gt=0, description="seconds; set by code")
    visual_intent: str = ""
    characters: list[str] = []
    locations: list[str] = []
    objects: list[str] = []
    action: str = ""
    emotion: str = ""
    camera: CameraSpec = CameraSpec()
    image_prompt: str = ""
    negative_prompt: str = ""
    voice: str | None = None
    music: str | None = None
    sfx: list[str] = []
    subtitle: str | None = None


class TimelineScene(BaseModel):
    """A scene with resolved timing and resolved asset URLs — the Remotion input."""

    scene_id: str
    start: float = Field(ge=0)
    duration: float = Field(gt=0)
    narration: str = ""
    subtitle: str | None = None
    image_src: str | None = None
    audio_src: str | None = None
    camera: CameraSpec = CameraSpec()


class Timeline(BaseModel):
    version: int = 1
    fps: int = 30
    width: int = 1920
    height: int = 1080
    scenes: list[TimelineScene]

    @property
    def duration_seconds(self) -> float:
        return max((s.start + s.duration for s in self.scenes), default=0.0)
