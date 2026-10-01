import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { makeRun, makeSource, mockApi, renderWithClient } from "@/test/utils";
import { AddSourceDialog, validateTranscriptInput, validateUrlInput } from "./add-source-dialog";
import { QueryClient } from "@tanstack/react-query";

afterEach(() => vi.unstubAllGlobals());

const file = (name: string, size = 10) => {
  const f = new File(["x".repeat(Math.min(size, 10))], name, { type: "text/plain" });
  Object.defineProperty(f, "size", { value: size });
  return f;
};

describe("client-side validation", () => {
  it("validates the URL", () => {
    expect(validateUrlInput("  ")).toMatch(/Enter a YouTube/);
    expect(validateUrlInput("youtu.be/x")).toMatch(/http/);
    expect(validateUrlInput(" https://youtu.be/dQw4w9WgXcQ ")).toBeNull();
  });

  it("validates transcript input like the server (title, extension, size, content)", () => {
    expect(validateTranscriptInput({ file: null, text: "hi", title: " " })).toMatch(/title/i);
    expect(validateTranscriptInput({ file: file("a.pdf"), text: "", title: "t" })).toMatch(
      /Unsupported/,
    );
    expect(validateTranscriptInput({ file: file("a.txt", 0), text: "", title: "t" })).toMatch(
      /empty/,
    );
    expect(
      validateTranscriptInput({ file: file("a.txt", 5 * 1024 * 1024 + 1), text: "", title: "t" }),
    ).toMatch(/too large/);
    expect(validateTranscriptInput({ file: null, text: "   ", title: "t" })).toMatch(
      /file or paste/,
    );
    expect(validateTranscriptInput({ file: file("A.SRT"), text: "", title: "t" })).toBeNull();
    expect(validateTranscriptInput({ file: null, text: "hello", title: "t" })).toBeNull();
  });
});

function open(initialTab: "url" | "upload" = "url") {
  const view = renderWithClient(<AddSourceDialog initialTab={initialTab} />);
  fireEvent.click(screen.getByRole("button", { name: /add source/i }));
  return view;
}

describe("AddSourceDialog", () => {
  it("opens with accessible labelled inputs", async () => {
    open();
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByLabelText("YouTube video URL")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Upload or paste" })).toBeInTheDocument();
  });

  it("rejects an empty URL without calling the API", async () => {
    const fetchMock = mockApi(() => undefined);
    open();
    fireEvent.click(await screen.findByRole("button", { name: "Add video" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/Enter a YouTube/);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows upload validation errors before any request", async () => {
    const fetchMock = mockApi(() => undefined);
    open("upload");
    fireEvent.click(await screen.findByRole("tab", { name: "Upload or paste" }));
    fireEvent.click(await screen.findByRole("button", { name: "Add transcript" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/title/i);

    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "My talk" } });
    fireEvent.change(screen.getByLabelText(/Transcript file/), {
      target: { files: [file("notes.pdf")] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add transcript" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/Unsupported file type/);

    fireEvent.change(screen.getByLabelText(/Transcript file/), {
      target: { files: [file("big.txt", 6 * 1024 * 1024)] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add transcript" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/too large/);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("posts the transcript as multipart FormData (no JSON content type)", async () => {
    const source = makeSource({ kind: "transcript", platform: "upload", url: null });
    const fetchMock = mockApi(() => ({
      status: 201,
      body: { source, run: null, already_exists: false, match: null, transcript: null },
    }));
    open("upload");
    fireEvent.click(await screen.findByRole("tab", { name: "Upload or paste" }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "My talk" } });
    fireEvent.change(screen.getByLabelText("Language (optional)"), { target: { value: "en" } });
    fireEvent.change(screen.getByLabelText(/Transcript file/), {
      target: { files: [file("talk.srt")] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add transcript" }));

    expect(await screen.findByText(/Added\./)).toBeInTheDocument();
    const init = fetchMock.mock.calls[0]![1] as RequestInit;
    expect(init.method).toBe("POST");
    const form = init.body as FormData;
    expect(form).toBeInstanceOf(FormData);
    expect(form.get("title")).toBe("My talk");
    expect(form.get("language")).toBe("en");
    expect((form.get("file") as File).name).toBe("talk.srt");
    expect(init.headers).not.toHaveProperty("Content-Type");
  });

  it("sends pasted text when no file is chosen", async () => {
    const fetchMock = mockApi(() => ({
      status: 201,
      body: {
        source: makeSource(),
        run: null,
        already_exists: false,
        match: null,
        transcript: null,
      },
    }));
    open("upload");
    fireEvent.click(await screen.findByRole("tab", { name: "Upload or paste" }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Pasted" } });
    fireEvent.change(screen.getByLabelText("Or paste text"), { target: { value: "hello world" } });
    fireEvent.click(screen.getByRole("button", { name: "Add transcript" }));
    await screen.findByText(/Added\./);
    const form = (fetchMock.mock.calls[0]![1] as RequestInit).body as FormData;
    expect(form.get("text")).toBe("hello world");
    expect(form.has("file")).toBe(false);
  });

  it("shows the duplicate notice with a link instead of adding twice", async () => {
    const source = makeSource({ id: "dup-1", title: "Already here" });
    mockApi(() => ({
      status: 200,
      body: { source, run: null, already_exists: true, match: "identity", transcript: null },
    }));
    open();
    fireEvent.change(await screen.findByLabelText("YouTube video URL"), {
      target: { value: "https://youtu.be/dQw4w9WgXcQ" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add video" }));
    const notice = await screen.findByRole("status");
    expect(notice).toHaveTextContent(/already in your library/i);
    expect(screen.getByRole("link", { name: "Already here" })).toHaveAttribute(
      "href",
      "/sources/videos/dup-1",
    );
  });

  it.each([
    [413, "file_too_large", "file exceeds max size of 5242880 bytes"],
    [422, "transcript_parse_error", "line 7: bad timestamp"],
    [409, "provider_not_configured", "yt-dlp is not installed; run `uv sync --extra ingestion`"],
  ])("renders the server detail inline for HTTP %i", async (status, code, detail) => {
    mockApi(() => ({ status, body: { detail, code } }));
    open();
    fireEvent.change(await screen.findByLabelText("YouTube video URL"), {
      target: { value: "https://youtu.be/dQw4w9WgXcQ" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add video" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(detail);
  });

  it("follows a started run to completion", async () => {
    const source = makeSource({ status: "importing", transcript_status: null, searchable: false });
    const run = makeRun({ id: "r9", status: "running" });
    mockApi((path, init) => {
      if (path === "/sources/from-url")
        return {
          status: 202,
          body: { source, run, already_exists: false, match: null, transcript: null },
        };
      if (path === "/runs/r9")
        return { ...run, status: "succeeded", finished_at: "2026-10-01T10:01:00Z" };
      if (init?.method === undefined) return undefined;
      return undefined;
    });
    open();
    fireEvent.change(await screen.findByLabelText("YouTube video URL"), {
      target: { value: "https://youtu.be/dQw4w9WgXcQ" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add video" }));
    await waitFor(() => expect(screen.getByText(/Added\./)).toBeInTheDocument());
    expect(screen.getByRole("link", { name: "Open the source" })).toHaveAttribute(
      "href",
      `/sources/videos/${source.id}`,
    );
  });

  it("explains a no-captions failure and points to the upload tab", async () => {
    const source = makeSource({
      status: "imported",
      transcript_status: "failed",
      searchable: false,
    });
    const run = makeRun({ id: "r8", status: "running" });
    mockApi((path) => {
      if (path === "/sources/from-url")
        return {
          status: 202,
          body: { source, run, already_exists: false, match: null, transcript: null },
        };
      if (path === "/runs/r8")
        return {
          ...run,
          status: "failed",
          error: { code: "no_captions", message: "No captions found", retryable: false },
        };
      return undefined;
    });
    open();
    fireEvent.change(await screen.findByLabelText("YouTube video URL"), {
      target: { value: "https://youtu.be/dQw4w9WgXcQ" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add video" }));
    const alert = await screen.findByText(/No captions found \(no_captions\)/);
    expect(alert).toBeInTheDocument();
    expect(screen.getByText(/Upload or paste tab/)).toBeInTheDocument();
  });
});

describe("attach mode (no-captions fallback)", () => {
  function openAttach() {
    const view = renderWithClient(
      <AddSourceDialog attachToSourceId="s1" label="Upload transcript instead" />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Upload transcript instead" }));
    return view;
  }

  it("has no title field, no URL tab, and never creates a source", async () => {
    mockApi(() => undefined);
    openAttach();
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.queryByLabelText("Title")).toBeNull();
    expect(screen.queryByRole("tab")).toBeNull();
    expect(screen.queryByLabelText("Reference URL (optional)")).toBeNull();
    expect(screen.getByLabelText(/Transcript file/)).toBeInTheDocument();
  });

  it("validates without a title", () => {
    expect(
      validateTranscriptInput({ file: null, text: "hello", title: "", attach: true }),
    ).toBeNull();
    expect(validateTranscriptInput({ file: null, text: "  ", title: "", attach: true })).toMatch(
      /file or paste/,
    );
  });

  it("posts multipart to /sources/{id}/transcript and refreshes that source and the library", async () => {
    const fetchMock = mockApi((path) =>
      path === "/sources/s1/transcript"
        ? { status: 200, body: makeSource({ id: "s1" }) }
        : undefined,
    );
    const { client } = openAttach();
    const invalidate = vi.spyOn(client as QueryClient, "invalidateQueries");
    fireEvent.change(await screen.findByLabelText(/Transcript file/), {
      target: { files: [file("talk.vtt")] },
    });
    fireEvent.change(screen.getByLabelText("Language (optional)"), { target: { value: "en" } });
    fireEvent.click(screen.getByRole("button", { name: "Add transcript" }));

    expect(await screen.findByText(/Transcript added/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]! as [string, RequestInit];
    expect(url).toMatch(/\/api\/v1\/sources\/s1\/transcript$/);
    expect(init.method).toBe("POST");
    const form = init.body as FormData;
    expect((form.get("file") as File).name).toBe("talk.vtt");
    expect(form.get("language")).toBe("en");
    expect(form.has("title")).toBe(false);
    expect(init.headers).not.toHaveProperty("Content-Type");
    await waitFor(() => {
      expect(invalidate).toHaveBeenCalledWith({ queryKey: ["/sources", "s1"] });
      expect(invalidate).toHaveBeenCalledWith({ queryKey: ["/sources"] });
    });
  });

  it("shows the busy message while an import is running (409 source_busy)", async () => {
    mockApi(() => ({
      status: 409,
      body: {
        detail: "An import is still running for this source; wait for it to finish.",
        code: "source_busy",
      },
    }));
    openAttach();
    fireEvent.change(await screen.findByLabelText("Or paste text"), { target: { value: "hello" } });
    fireEvent.click(screen.getByRole("button", { name: "Add transcript" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/import is still running/i);
    expect(screen.queryByText(/Transcript added/)).toBeNull();
  });

  it("shows the parse error with its line number (422 transcript_parse_error)", async () => {
    mockApi(() => ({
      status: 422,
      body: { detail: "line 12: invalid timestamp '00:61:00'", code: "transcript_parse_error" },
    }));
    openAttach();
    fireEvent.change(await screen.findByLabelText(/Transcript file/), {
      target: { files: [file("bad.srt")] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add transcript" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("line 12: invalid timestamp");
  });

  it.each([
    [413, "file_too_large", "file exceeds max size of 5242880 bytes"],
    [422, "unsupported_file_type", "unsupported file type .pdf"],
  ])("shows server errors inline (HTTP %i %s)", async (status, code, detail) => {
    mockApi(() => ({ status, body: { detail, code } }));
    openAttach();
    fireEvent.change(await screen.findByLabelText("Or paste text"), { target: { value: "hello" } });
    fireEvent.click(screen.getByRole("button", { name: "Add transcript" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(detail);
  });
});
