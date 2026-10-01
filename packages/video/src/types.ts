import { z } from "zod";

/**
 * Mirrors apps/api/app/schemas/scene.py (CameraSpec, TimelineScene, Timeline). Keep in sync:
 * `packages/video/src/contract.test.ts` and `apps/api/tests/test_timeline_contract.py` both check
 * the canonical samples in packages/schemas/samples (regenerate with `make schemas`), and the
 * Python test also compares the enum literals below with the Pydantic Literals.
 * See docs/architecture/data-flow.md.
 */
export const cameraShot = z.enum([
  "wide",
  "medium",
  "close_up",
  "extreme_close_up",
  "over_shoulder",
  "aerial",
]);

export const cameraMovement = z.enum([
  "static",
  "slow_zoom_in",
  "slow_zoom_out",
  "pan_left",
  "pan_right",
  "tilt_up",
  "tilt_down",
]);

export const cameraSpec = z.object({
  shot: cameraShot.default("medium"),
  movement: cameraMovement.default("static"),
});

export const timelineScene = z.object({
  scene_id: z.string(),
  start: z.number().min(0),
  duration: z.number().positive(),
  narration: z.string().default(""),
  subtitle: z.string().nullable().default(null),
  image_src: z.string().nullable().default(null),
  audio_src: z.string().nullable().default(null),
  camera: cameraSpec.default({ shot: "medium", movement: "static" }),
});

export const timelineSchema = z.object({
  version: z.number().int().default(1),
  fps: z.number().int().positive().default(30),
  width: z.number().int().positive().default(1920),
  height: z.number().int().positive().default(1080),
  scenes: z.array(timelineScene),
});

export type Timeline = z.infer<typeof timelineSchema>;
export type TimelineScene = z.infer<typeof timelineScene>;
export type CameraMovement = z.infer<typeof cameraMovement>;
export type CameraShot = z.infer<typeof cameraShot>;
