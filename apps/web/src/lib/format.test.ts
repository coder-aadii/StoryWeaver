import { describe, expect, it } from "vitest";
import { formatDuration, formatTimestamp } from "./format";

describe("formatTimestamp", () => {
  it("formats mm:ss and h:mm:ss", () => {
    expect(formatTimestamp(0)).toBe("00:00");
    expect(formatTimestamp(65.9)).toBe("01:05");
    expect(formatTimestamp(3599)).toBe("59:59");
    expect(formatTimestamp(3600)).toBe("1:00:00");
    expect(formatTimestamp(3725)).toBe("1:02:05");
  });
  it("handles missing and invalid values", () => {
    expect(formatTimestamp(null)).toBe("—");
    expect(formatTimestamp(undefined)).toBe("—");
    expect(formatTimestamp(Number.NaN)).toBe("—");
    expect(formatTimestamp(-5)).toBe("00:00");
  });
});

describe("formatDuration", () => {
  it("uses seconds below 90 s and minutes above", () => {
    expect(formatDuration(45)).toBe("45 s");
    expect(formatDuration(1800)).toBe("30 min");
    expect(formatDuration(null)).toBe("—");
  });
});
