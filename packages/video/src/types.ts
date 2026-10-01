import { z } from "zod";

/** Mirrors apps/api/app/schemas/scene.py (Timeline). Keep in sync; see docs/architecture/data-flow.md. */
export const cameraMovement = z.enum([
  "static",
  "slow_zoom_in",
  "slow_zoom_out",
  "pan_left",
  "pan_right",
  "tilt_up",
  "tilt_down",
]);

export const timelineScene = z.object({
  scene_id: z.string(),
  start: z.number().min(0),
  duration: z.number().positive(),
  narration: z.string().default(""),
  subtitle: z.string().nullable().default(null),
  image_src: z.string().nullable().default(null),
  audio_src: z.string().nullable().default(null),
  camera: z.object({
    shot: z.string().default("medium"),
    movement: cameraMovement.default("static"),
  }),
});

export const timelineSchema = z.object({
  version: z.number().default(1),
  fps: z.number().int().positive().default(30),
  width: z.number().int().positive().default(1920),
  height: z.number().int().positive().default(1080),
  scenes: z.array(timelineScene),
});

export type Timeline = z.infer<typeof timelineSchema>;
export type TimelineScene = z.infer<typeof timelineScene>;
export type CameraMovement = z.infer<typeof cameraMovement>;
