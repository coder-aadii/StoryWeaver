import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { timelineSchema } from "./types";

/**
 * Contract with the Pydantic models: the samples in packages/schemas/samples are generated from
 * Pydantic (`make schemas`) and also checked by apps/api/tests/test_timeline_contract.py.
 */
const dir = fileURLToPath(new URL("../../schemas/samples/", import.meta.url));
const read = (name: string): unknown => JSON.parse(readFileSync(dir + name, "utf8"));
const names = readdirSync(dir).filter((n) => n.startsWith("timeline."));

describe("Timeline zod mirror vs Pydantic samples", () => {
  it("finds the generated samples", () => {
    expect(names.length).toBeGreaterThan(5);
  });

  it("a fully specified valid timeline parses to itself", () => {
    const full = read("timeline.valid.full.json");
    expect(timelineSchema.parse(full)).toEqual(full);
  });

  it("defaults applied by zod equal the defaults applied by Pydantic", () => {
    expect(timelineSchema.parse(read("timeline.valid.minimal.input.json"))).toEqual(
      read("timeline.valid.minimal.expected.json"),
    );
  });

  for (const name of names.filter((n) => n.startsWith("timeline.invalid."))) {
    it(`rejects ${name}`, () => {
      expect(timelineSchema.safeParse(read(name)).success).toBe(false);
    });
  }
});
