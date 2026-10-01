import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./api";

afterEach(() => vi.unstubAllGlobals());

function respond(status: number, body: unknown, statusText = "") {
  return vi
    .fn()
    .mockResolvedValue(
      new Response(typeof body === "string" ? body : JSON.stringify(body), { status, statusText }),
    );
}

describe("api", () => {
  it("returns parsed JSON", async () => {
    vi.stubGlobal("fetch", respond(200, [{ id: "1" }]));
    expect(await api("/projects")).toEqual([{ id: "1" }]);
  });

  it("wraps non-2xx in ApiError with status", async () => {
    vi.stubGlobal("fetch", respond(404, "", "Not Found"));
    await expect(api("/projects/x")).rejects.toMatchObject({
      status: 404,
      message: "404 Not Found",
    });
  });

  it("gives a helpful message when the API is down", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fail")));
    await expect(api("/projects")).rejects.toBeInstanceOf(ApiError);
    await expect(api("/projects")).rejects.toThrow(/Is it running/);
  });

  it("returns undefined for 204", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    expect(await api<void>("/sources/1", { method: "DELETE" })).toBeUndefined();
  });
});

describe("error bodies", () => {
  it("surfaces the {detail, code} message and code", async () => {
    vi.stubGlobal(
      "fetch",
      respond(413, { detail: "file exceeds max size of 5242880 bytes", code: "file_too_large" }),
    );
    const err = await api("/sources/from-transcript", { method: "POST" }).catch((e: ApiError) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({
      status: 413,
      code: "file_too_large",
      message: "file exceeds max size of 5242880 bytes",
    });
  });

  it("joins FastAPI validation messages and strips the 'Value error, ' prefix", async () => {
    vi.stubGlobal(
      "fetch",
      respond(422, {
        detail: [
          { type: "value_error", loc: ["body"], msg: "Value error, not a YouTube URL" },
          {
            type: "string_too_short",
            loc: ["body", "title"],
            msg: "String should have at least 1 character",
          },
        ],
      }),
    );
    const err = (await api("/sources", { method: "POST" }).catch((e: unknown) => e)) as ApiError;
    expect(err.message).toBe("not a YouTube URL; String should have at least 1 character");
    expect(err.code).toBeNull();
  });

  it("falls back to the status line for non-JSON error bodies", async () => {
    vi.stubGlobal("fetch", respond(502, "<html>bad gateway</html>", "Bad Gateway"));
    await expect(api("/x")).rejects.toMatchObject({ status: 502, message: "502 Bad Gateway" });
  });
});

describe("request headers", () => {
  it("sets JSON content type only for string bodies", async () => {
    const fn = respond(200, {});
    vi.stubGlobal("fetch", fn);
    await api("/projects", { method: "POST", body: JSON.stringify({ title: "x" }) });
    expect((fn.mock.calls[0]![1] as RequestInit).headers).toMatchObject({
      "Content-Type": "application/json",
    });
  });

  it("does NOT set Content-Type for FormData (the browser adds the multipart boundary)", async () => {
    const fn = respond(200, {});
    vi.stubGlobal("fetch", fn);
    const form = new FormData();
    form.append("title", "t");
    await api("/sources/from-transcript", { method: "POST", body: form });
    const init = fn.mock.calls[0]![1] as RequestInit;
    expect(init.body).toBe(form);
    expect(init.headers).not.toHaveProperty("Content-Type");
  });

  it("sends no Content-Type on a plain GET (avoids a CORS preflight)", async () => {
    const fn = respond(200, []);
    vi.stubGlobal("fetch", fn);
    await api("/projects");
    expect((fn.mock.calls[0]![1] as RequestInit).headers).toEqual({});
  });
});
