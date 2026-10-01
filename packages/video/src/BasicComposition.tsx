import { AbsoluteFill, Audio, Img, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import { cameraTransform } from "./camera";
import type { Timeline, TimelineScene } from "./types";

const SceneView: React.FC<{ scene: TimelineScene; index: number }> = ({ scene, index }) => {
  const frame = useCurrentFrame(); // relative to the enclosing Sequence
  const { fps } = useVideoConfig();
  const total = Math.max(Math.round(scene.duration * fps), 1);
  const cam = cameraTransform(scene.camera.movement, frame / total);
  const hue = (index * 47) % 360;

  return (
    <AbsoluteFill style={{ background: `linear-gradient(135deg, hsl(${hue} 35% 14%), hsl(${hue + 40} 40% 8%))` }}>
      <AbsoluteFill
        style={{
          transform: `scale(${cam.scale}) translate(${cam.x}%, ${cam.y}%)`,
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        {scene.image_src ? (
          <Img src={scene.image_src} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        ) : (
          <div
            style={{
              width: "70%",
              height: "62%",
              border: "4px dashed rgba(255,255,255,0.35)",
              borderRadius: 24,
              color: "rgba(255,255,255,0.5)",
              fontSize: 42,
              fontFamily: "sans-serif",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            Image placeholder · {scene.scene_id}
          </div>
        )}
      </AbsoluteFill>
      {scene.audio_src ? <Audio src={scene.audio_src} /> : null}
      {scene.subtitle ? (
        <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 72 }}>
          <div
            style={{
              maxWidth: "80%",
              padding: "14px 28px",
              borderRadius: 12,
              background: "rgba(0,0,0,0.6)",
              color: "white",
              fontFamily: "sans-serif",
              fontSize: 44,
              textAlign: "center",
            }}
          >
            {scene.subtitle}
          </div>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};

export const BasicComposition: React.FC<Timeline> = ({ scenes, fps }) => (
  <AbsoluteFill style={{ background: "black" }}>
    {scenes.map((scene, i) => (
      <Sequence
        key={scene.scene_id}
        from={Math.round(scene.start * fps)}
        durationInFrames={Math.max(Math.round(scene.duration * fps), 1)}
      >
        <SceneView scene={scene} index={i} />
      </Sequence>
    ))}
  </AbsoluteFill>
);

export function timelineDurationInFrames(t: Timeline): number {
  const end = t.scenes.reduce((m, s) => Math.max(m, s.start + s.duration), 0);
  return Math.max(Math.round(end * t.fps), 1);
}
