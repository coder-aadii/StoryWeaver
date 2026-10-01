import { Composition } from "remotion";
import { BasicComposition, timelineDurationInFrames } from "./BasicComposition";
import { timelineSchema, type Timeline } from "./types";

const defaultProps: Timeline = timelineSchema.parse({
  scenes: [
    { scene_id: "scene_001", start: 0, duration: 3, subtitle: "Preview", camera: { movement: "slow_zoom_in" } },
  ],
});

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Basic"
    component={BasicComposition}
    schema={timelineSchema}
    defaultProps={defaultProps}
    durationInFrames={90}
    fps={30}
    width={1920}
    height={1080}
    calculateMetadata={({ props }) => ({
      durationInFrames: timelineDurationInFrames(props),
      fps: props.fps,
      width: props.width,
      height: props.height,
    })}
  />
);
