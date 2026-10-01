"""Deterministic timing: code, not an LLM, decides durations and start times."""

from app.schemas.scene import SceneSpec, Timeline, TimelineScene

WORDS_PER_SECOND = 2.5  # ~150 wpm narration
MIN_SCENE_SECONDS = 2.0
MAX_SCENE_SECONDS = 7.0


def estimate_duration(narration: str) -> float:
    """Fallback estimate when real audio length is unknown. Measured audio always wins."""
    seconds = len(narration.split()) / WORDS_PER_SECOND
    return round(min(max(seconds, MIN_SCENE_SECONDS), MAX_SCENE_SECONDS), 3)


def build_timeline(scenes: list[SceneSpec], *, fps: int = 30) -> Timeline:
    cursor = 0.0
    out: list[TimelineScene] = []
    for s in sorted(scenes, key=lambda s: s.sequence):
        duration = s.duration or estimate_duration(s.narration)
        out.append(
            TimelineScene(
                scene_id=s.scene_id, start=round(cursor, 3), duration=duration,
                narration=s.narration, subtitle=s.subtitle or s.narration, camera=s.camera,
            )
        )  # fmt: skip
        cursor += duration
    return Timeline(fps=fps, scenes=out)
