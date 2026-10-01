import { afterEach, describe, expect, it, vi } from "vitest";
import { mockApi } from "@/test/utils";
import {
  addSourceFromTranscript,
  addSourceFromUrl,
  attachTranscript,
  deleteProjectSource,
  deleteSource,
  getChunks,
  getRun,
  getSource,
  getTranscript,
  getUsage,
  listProjectSources,
  listRuns,
  listSources,
  putProjectSource,
  qs,
  retrySource,
  searchSources,
} from "./sources-api";

afterEach(() => vi.unstubAllGlobals());

describe("qs", () => {
  it("skips empty values and encodes the rest", () => {
    expect(qs({ q: "ice age", limit: 20, offset: 0, used: undefined, kind: null, x: "" })).toBe(
      "?q=ice+age&limit=20&offset=0",
    );
    expect(qs({})).toBe("");
    expect(qs({ used: false })).toBe("?used=false");
  });
});

describe("endpoints", () => {
  it("calls the documented routes with the right methods and bodies", async () => {
    const calls: string[] = [];
    const fn = mockApi((path, init, q) => {
      calls.push(`${init?.method ?? "GET"} ${path}${q?.toString() ? `?${q}` : ""}`);
      return path.endsWith("/usage") || /\/projects\/[^/]+\/sources$/.test(path)
        ? []
        : { status: path.includes("DEL") ? 204 : 200, body: {} };
    });
    await listSources({ limit: 5, used: false });
    await getSource("s1");
    await addSourceFromUrl("https://youtu.be/dQw4w9WgXcQ");
    await addSourceFromTranscript(new FormData());
    await retrySource("s1");
    await deleteSource("DEL1");
    await searchSources({ q: "ice", exclude_used: true, source_id: "s1" });
    await getTranscript("s1", { limit: 50, offset: 50 });
    await getChunks("s1");
    await getUsage("s1");
    await getRun("r1");
    await listRuns("s1", { limit: 10 });
    await attachTranscript("s1", new FormData());
    await listProjectSources("p1");
    await putProjectSource("p1", "s1", "primary");
    await deleteProjectSource("p1", "DEL1");
    expect(calls).toEqual([
      "GET /sources?limit=5&used=false",
      "GET /sources/s1",
      "POST /sources/from-url",
      "POST /sources/from-transcript",
      "POST /sources/s1/retry",
      "DELETE /sources/DEL1",
      "GET /sources/search?q=ice&exclude_used=true&source_id=s1",
      "GET /sources/s1/transcript?limit=50&offset=50",
      "GET /sources/s1/chunks",
      "GET /sources/s1/usage",
      "GET /runs/r1",
      "GET /runs?subject_id=s1&limit=10",
      "POST /sources/s1/transcript",
      "GET /projects/p1/sources",
      "PUT /projects/p1/sources/s1",
      "DELETE /projects/p1/sources/DEL1",
    ]);
    expect(JSON.parse((fn.mock.calls[2]![1] as RequestInit).body as string)).toEqual({
      url: "https://youtu.be/dQw4w9WgXcQ",
    });
  });
});
