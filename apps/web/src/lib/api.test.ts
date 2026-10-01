import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("api", () => {
  it("returns parsed JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify([{ id: "1" }]))));
    expect(await api("/projects")).toEqual([{ id: "1" }]);
  });
  it("wraps non-2xx in ApiError with status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("", { status: 404, statusText: "Not Found" })),
    );
    await expect(api("/projects/x")).rejects.toMatchObject({ status: 404 });
  });
  it("gives a helpful message when the API is down", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fail")));
    await expect(api("/projects")).rejects.toBeInstanceOf(ApiError);
    await expect(api("/projects")).rejects.toThrow(/Is it running/);
  });
});
