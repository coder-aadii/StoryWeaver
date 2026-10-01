import type { CameraMovement } from "./types";

export interface CameraTransform {
  scale: number;
  x: number; // percent of frame
  y: number;
}

/** Pure, deterministic camera path. `t` is scene progress in [0, 1]. */
export function cameraTransform(movement: CameraMovement, t: number): CameraTransform {
  const p = Math.min(Math.max(t, 0), 1);
  switch (movement) {
    case "slow_zoom_in":
      return { scale: 1 + 0.12 * p, x: 0, y: 0 };
    case "slow_zoom_out":
      return { scale: 1.12 - 0.12 * p, x: 0, y: 0 };
    case "pan_left":
      return { scale: 1.12, x: 3 - 6 * p, y: 0 };
    case "pan_right":
      return { scale: 1.12, x: -3 + 6 * p, y: 0 };
    case "tilt_up":
      return { scale: 1.12, x: 0, y: 3 - 6 * p };
    case "tilt_down":
      return { scale: 1.12, x: 0, y: -3 + 6 * p };
    default:
      return { scale: 1, x: 0, y: 0 };
  }
}
