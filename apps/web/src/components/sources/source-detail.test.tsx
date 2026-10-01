import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { makeRun, makeSource, mockApi, page, renderWithClient } from "@/test/utils";
import type { SourceDetail } from "@/lib/sources-api";
import { SourceDetailView, deleteErrorMessage } from "./source-detail";
import { ApiError } from "@/lib/api";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/sources/videos/s1",
  useSearchParams: () => new URLSearchParams(),
}));

afterEach(() => {
  vi.unstubAllGlobals();
  replace.mockReset();
});

const detail = (over: Partial<SourceDetail> = {}): SourceDetail => ({
  ...makeSource({ id: "s1" }),
  description: "A talk about surviving the ice age.",
  published_at: "2026-01-01T00:00:00Z",
  fingerprint: "abc",
  transcript: {
    id: "t1",
    version: 1,
    status: "ready",
    origin: "auto",
    language: "en",
    segment_count: 2,
    char_count: 40,
    timed: true,
    normalizer_version: "1",
    error: null,
    created_at: "2026-10-01T10:00:00Z",
  },
  active_run: null,
  ...over,
});

function routes(
  source: SourceDetail,
  extra: (path: string, init?: RequestInit, q?: URLSearchParams) => unknown = () => undefined,
) {
  return mockApi((path, init, q) => {
    // Writes go to the test's own handler first; the defaults below only answer GETs.
    if (init?.method && init.method !== "GET") return extra(path, init, q);
    if (path === "/sources/s1") return source;
    if (path === "/sources/s1/transcript")
      return {
        transcript: source.transcript,
        text: "hello there general kenobi",
        segments: page([
          { start: 5, end: 8, text: "hello there" },
          { start: 3725, end: 3730, text: "general kenobi" },
        ]),
      };
    if (path === "/sources/s1/usage") return [];
    if (path === "/projects") return [];
    return extra(path, init, q);
  });
}

describe("SourceDetailView", () => {
  it("shows metadata, a safe thumbnail, and the transcript with timestamps", async () => {
    routes(detail({ thumbnail_url: "https://i.ytimg.com/vi/x/hq.jpg" }));
    renderWithClient(<SourceDetailView id="s1" />);
    expect(await screen.findByRole("heading", { name: "Ice Age Survival" })).toBeInTheDocument();
    const img = screen.getByAltText("Thumbnail of Ice Age Survival");
    expect(img).toHaveAttribute("referrerpolicy", "no-referrer");
    expect(screen.getByText("30 min")).toBeInTheDocument();
    expect(await screen.findByText("hello there")).toBeInTheDocument();
    expect(screen.getByText("00:05")).toBeInTheDocument();
    expect(screen.getByText("1:02:05")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "Open original" });
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("omits timestamps for untimed (plain text) transcripts", async () => {
    const s = detail();
    s.transcript = { ...s.transcript!, timed: false };
    routes(s);
    renderWithClient(<SourceDetailView id="s1" />);
    await screen.findByText("hello there");
    expect(screen.queryByText("00:05")).toBeNull();
    expect(screen.getByText(/no timestamps/)).toBeInTheDocument();
  });

  it("shows the failure panel with the error, Retry, and the upload fallback", async () => {
    const calls: string[] = [];
    routes(
      detail({
        status: "imported",
        transcript_status: "failed",
        transcript_error: "No captions found (no_captions)",
        searchable: false,
        transcript: null,
      }),
      (path, init) => {
        calls.push(`${init?.method ?? "GET"} ${path}`);
        if (path === "/sources/s1/retry") return { status: 202, body: { run: makeRun() } };
        return undefined;
      },
    );
    renderWithClient(<SourceDetailView id="s1" />);
    const panel = await screen.findByRole("alert");
    expect(panel).toHaveTextContent("No captions found (no_captions)");
    expect(
      within(panel).getByRole("button", { name: "Upload transcript instead" }),
    ).toBeInTheDocument();
    fireEvent.click(within(panel).getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(calls).toContain("POST /sources/s1/retry"));
  });

  it("'Upload transcript instead' attaches to THIS source (no title, no new source)", async () => {
    const calls: string[] = [];
    routes(
      detail({ transcript_status: "failed", searchable: false, transcript: null }),
      (path, init) => {
        calls.push(`${init?.method ?? "GET"} ${path}`);
        if (path === "/sources/s1/transcript" && init?.method === "POST")
          return { status: 200, body: detail() };
        return undefined;
      },
    );
    renderWithClient(<SourceDetailView id="s1" />);
    fireEvent.click(await screen.findByRole("button", { name: "Upload transcript instead" }));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.queryByLabelText("Title")).toBeNull();
    fireEvent.change(screen.getByLabelText("Or paste text"), { target: { value: "hello there" } });
    fireEvent.click(screen.getByRole("button", { name: "Add transcript" }));
    expect(await screen.findByText(/Transcript added/)).toBeInTheDocument();
    expect(calls).toContain("POST /sources/s1/transcript");
    expect(calls).not.toContain("POST /sources/from-transcript");
  });

  it("explains a missing source", async () => {
    mockApi(() => ({ status: 404, body: { detail: "sources not found", code: "not_found" } }));
    renderWithClient(<SourceDetailView id="nope" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Source not found.");
  });

  it("searches inside the source using the server-side source_id filter", async () => {
    const seen: URLSearchParams[] = [];
    routes(detail(), (path, _i, q) => {
      if (path === "/sources/search") {
        seen.push(q!);
        return page([
          {
            source: makeSource({ id: "s1" }),
            chunk_id: "c1",
            chunk_index: 0,
            snippet: "the <mark>ice</mark>",
            start_seconds: 5,
            end_seconds: 8,
            rank: 1,
          },
        ]);
      }
      return undefined;
    });
    renderWithClient(<SourceDetailView id="s1" />);
    fireEvent.change(await screen.findByLabelText("Word or phrase"), { target: { value: "ice" } });
    fireEvent.submit(screen.getByRole("search"));
    const list = await screen.findByRole("list", { name: "Matches in this source" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(1);
    expect(seen[0]!.get("source_id")).toBe("s1");
    expect(seen[0]!.get("q")).toBe("ice");
  });

  it("lists projects using the source and links it to another project", async () => {
    const calls: string[] = [];
    mockApi((path, init) => {
      calls.push(`${init?.method ?? "GET"} ${path}`);
      if (path === "/sources/s1")
        return detail({ transcript: null, transcript_status: null, searchable: false });
      if (path === "/sources/s1/usage")
        return [
          {
            project_id: "p1",
            project_title: "Documentary",
            role: "primary",
            linked_at: "2026-10-01T00:00:00Z",
          },
        ];
      if (path === "/projects")
        return [
          {
            id: "p1",
            title: "Documentary",
            description: null,
            status: "draft",
            error: null,
            created_at: "2026-10-01T00:00:00Z",
          },
          {
            id: "p2",
            title: "Short film",
            description: null,
            status: "draft",
            error: null,
            created_at: "2026-10-01T00:00:00Z",
          },
        ];
      if (path === "/projects/p2/sources/s1")
        return {
          status: 200,
          body: { source: makeSource(), role: "primary", linked_at: "2026-10-01T00:00:00Z" },
        };
      return undefined;
    });
    renderWithClient(<SourceDetailView id="s1" />);
    expect(await screen.findByRole("link", { name: "Documentary" })).toHaveAttribute(
      "href",
      "/projects/p1",
    );
    const picker = await screen.findByLabelText("Add to project");
    await waitFor(() =>
      expect(within(picker).getByRole("option", { name: "Short film" })).toBeInTheDocument(),
    );
    expect(within(picker).queryByRole("option", { name: "Documentary" })).toBeNull(); // already linked
    fireEvent.change(picker, { target: { value: "p2" } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));
    await waitFor(() => expect(calls).toContain("PUT /projects/p2/sources/s1"));
  });

  it("shows import progress while a run is active", async () => {
    routes(
      detail({
        active_run: makeRun({ status: "running", progress: { step: "fetching captions" } }),
        transcript: null,
        transcript_status: null,
        searchable: false,
      }),
      (path) =>
        path === "/runs/22222222-2222-2222-2222-222222222222"
          ? makeRun({ status: "running" })
          : undefined,
    );
    renderWithClient(<SourceDetailView id="s1" />);
    expect(await screen.findByText(/Import running \(fetching captions\)/)).toBeInTheDocument();
  });

  describe("delete", () => {
    it("asks for confirmation, deletes, and returns to the library", async () => {
      const calls: string[] = [];
      routes(detail(), (path, init) => {
        calls.push(`${init?.method ?? "GET"} ${path}`);
        if (path === "/sources/s1" && init?.method === "DELETE") return { status: 204 };
        return undefined;
      });
      renderWithClient(<SourceDetailView id="s1" />);
      fireEvent.click(await screen.findByRole("button", { name: "Delete" }));
      const dialog = await screen.findByRole("dialog");
      expect(dialog).toHaveTextContent("Delete this source?");
      expect(calls).not.toContain("DELETE /sources/s1"); // nothing happens before confirming
      fireEvent.click(within(dialog).getByRole("button", { name: "Delete source" }));
      await waitFor(() => expect(calls).toContain("DELETE /sources/s1"));
      await waitFor(() => expect(replace).toHaveBeenCalledWith("/sources/videos"));
    });

    it("cancel closes the dialog without deleting", async () => {
      const calls: string[] = [];
      routes(detail(), (path, init) => {
        calls.push(`${init?.method ?? "GET"} ${path}`);
        return undefined;
      });
      renderWithClient(<SourceDetailView id="s1" />);
      fireEvent.click(await screen.findByRole("button", { name: "Delete" }));
      fireEvent.click(await screen.findByRole("button", { name: "Cancel" }));
      await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
      expect(calls).not.toContain("DELETE /sources/s1");
      expect(replace).not.toHaveBeenCalled();
    });

    it("tells the user to unlink the source first when it is in use (409 source_in_use)", async () => {
      routes(detail(), (path, init) =>
        path === "/sources/s1" && init?.method === "DELETE"
          ? { status: 409, body: { detail: "source is used by 1 project", code: "source_in_use" } }
          : undefined,
      );
      renderWithClient(<SourceDetailView id="s1" />);
      fireEvent.click(await screen.findByRole("button", { name: "Delete" }));
      const dialog = await screen.findByRole("dialog");
      fireEvent.click(within(dialog).getByRole("button", { name: "Delete source" }));
      expect(await within(dialog).findByRole("alert")).toHaveTextContent(
        /unlink it from its projects first/i,
      );
      expect(replace).not.toHaveBeenCalled();
    });

    it("deleteErrorMessage passes other errors through unchanged", () => {
      expect(deleteErrorMessage(new ApiError(500, "boom", "internal_error"))).toBe("boom");
      expect(deleteErrorMessage(new ApiError(409, "x", "source_in_use"))).toMatch(
        /unlink it from its projects first/i,
      );
    });
  });
});
