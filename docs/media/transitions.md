# Transitions

> Cuts and effects between scenes/shots.

## Status

**Planned — not implemented.** Scenes are placed back-to-back with hard cuts: each is a Remotion `<Sequence>` starting at `round(start × fps)` with no overlap, fade or effect.

## Current behaviour

`BasicComposition` renders scenes sequentially; the timeline schema has no transition field; `build_timeline` creates no overlaps or gaps. Between scenes the picture and any `audio_src` simply cut.

## Target Architecture

- **Types (closed set, code-implemented):** hard cut (default), crossfade/dissolve, fade through black, simple wipe/slide, and a few narrative ones (e.g. match-on-motion) later. Fewer, consistently used transitions look more professional than many.
- **Timeline representation (proposal, Decision pending):** each boundary carries `{type, duration}`; the builder converts transitions into overlapping sequence windows (the incoming scene starts early by the transition duration) while keeping total duration consistent and audio unaffected.
- **Selection:** AI suggests transition *intent* (e.g. "time jump", "tense cut") per boundary; code maps to a type and enforces rules (no transition longer than a fraction of the shorter scene; hard cut within an act, dissolve at act changes).
- **Audio:** narration continues across visual crossfades; music crossfades follow act boundaries ([music-and-sfx](music-and-sfx.md)).
- **Implementation options:** Remotion `@remotion/transitions` package or manual opacity interpolation over overlapping `<Sequence>`s; FFmpeg `xfade` only if rendering moves out of Remotion ([ffmpeg](ffmpeg.md)). Not evaluated.

## Failure modes

Transition longer than the scene (clamp); audio/visual desync when sequences overlap (compute overlap in the builder, not in the component); excessive effects.

## Open questions

Per-project default transition; how it interacts with multi-shot scenes; whether QA checks transition counts.

## Related

[camera-motion](camera-motion.md) · [timeline-specification](timeline-specification.md) · [remotion](remotion.md)
