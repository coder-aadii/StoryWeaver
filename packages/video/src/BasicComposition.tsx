import { AbsoluteFill, Audio, Img, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { cameraTransform } from "./camera";
import type { Timeline, TimelineScene } from "./types";

/** Maps a timeline asset reference to something the browser/renderer can load. */
export type AssetResolver = (src: string) => string;

/** Use the reference as given (URLs, data: URIs). This is what the web Player uses. */
export const rawAsset: AssetResolver = (src) => src;

/**
 * Resolve project-relative keys (e.g. "images/scene_001.png") against Remotion's public dir via
 * `staticFile()` (rendered with `--public-dir`). Absolute http(s)://, data: and "/" references are
 * left untouched. See docs/decisions/ADR-009-render-asset-resolution.md.
 */
export const publicDirAsset: AssetResolver = (src) =>
  /^(https?:|data:|\/)/.test(src) ? src : staticFile(src);

const SceneView: React.FC<{ scene: TimelineScene; index: number; resolve: AssetResolver }> = ({
  scene,
  index,
  resolve,
}) => {
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
          <Img src={resolve(scene.image_src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
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
      {scene.audio_src ? <Audio src={resolve(scene.audio_src)} /> : null}
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

export function createComposition(resolve: AssetResolver): React.FC<Timeline> {
  const Composition: React.FC<Timeline> = ({ scenes, fps }) => (
    <AbsoluteFill style={{ background: "black" }}>
      {scenes.map((scene, i) => (
        <Sequence
          key={scene.scene_id}
          from={Math.round(scene.start * fps)}
          durationInFrames={Math.max(Math.round(scene.duration * fps), 1)}
        >
          <SceneView scene={scene} index={i} resolve={resolve} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
  return Composition;
}

/** Player/preview composition: asset references are used as given. */
export const BasicComposition = createComposition(rawAsset);

/** Render composition for the asset-path spike: references resolve through `staticFile()`. */
export const AssetComposition = createComposition(publicDirAsset);

export function timelineDurationInFrames(t: Timeline): number {
  const end = t.scenes.reduce((m, s) => Math.max(m, s.start + s.duration), 0);
  return Math.max(Math.round(end * t.fps), 1);
}
