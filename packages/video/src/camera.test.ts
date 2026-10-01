import { describe, expect, it } from "vitest";
import { cameraTransform } from "./camera";
import { timelineSchema } from "./types";
import sample from "../sample/timeline.json";

describe("cameraTransform", () => {
  it("zooms in monotonically and clamps progress", () => {
    expect(cameraTransform("slow_zoom_in", 0).scale).toBe(1);
    expect(cameraTransform("slow_zoom_in", 1).scale).toBeCloseTo(1.12);
    expect(cameraTransform("slow_zoom_in", 5).scale).toBeCloseTo(1.12);
  });
  it("static does not move", () => {
    expect(cameraTransform("static", 0.5)).toEqual({ scale: 1, x: 0, y: 0 });
  });
});

describe("sample timeline", () => {
  it("validates against the schema", () => {
    expect(timelineSchema.parse(sample).scenes).toHaveLength(3);
  });
});
