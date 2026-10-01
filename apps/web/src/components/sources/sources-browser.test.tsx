import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { makeSource, mockApi, page, renderWithClient } from "@/test/utils";
import { SourcesBrowser } from "./sources-browser";

const replace = vi.fn();
let search = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/sources/videos",
  useSearchParams: () => new URLSearchParams(search),
}));

beforeEach(() => {
  search = "";
  replace.mockReset();
});
afterEach(() => vi.unstubAllGlobals());

describe("SourcesBrowser", () => {
  it("explains both ways to add a source when the library is empty", async () => {
    mockApi((path) => (path === "/sources" ? page([]) : undefined));
    renderWithClient(<SourcesBrowser />);
    expect(await screen.findByText("Your library is empty")).toBeInTheDocument();
    expect(screen.getByText(/YouTube video URL/)).toBeInTheDocument();
    expect(screen.getByText(/upload a transcript/i)).toBeInTheDocument();
  });

  it("shows a loading state, then the list", async () => {
    mockApi((path) =>
      path === "/sources" ? page([makeSource({ title: "Ice Age Survival" })]) : undefined,
    );
    renderWithClient(<SourcesBrowser />);
    expect(screen.getByLabelText("Loading")).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Ice Age Survival" })).toBeInTheDocument();
  });

  it("shows the API error when the list cannot be loaded", async () => {
    mockApi(() => ({ status: 500, body: { detail: "database is down", code: "internal_error" } }));
    renderWithClient(<SourcesBrowser />);
    expect(await screen.findByRole("alert")).toHaveTextContent("database is down");
  });

  it("requests only unused sources when the toggle is on", async () => {
    const fetchMock = mockApi((path) => (path === "/sources" ? page([]) : undefined));
    renderWithClient(<SourcesBrowser />);
    await screen.findByText("Your library is empty");
    fireEvent.click(screen.getByLabelText("Hide sources already used in a project"));
    await waitFor(() =>
      expect(fetchMock.mock.calls.some((c) => String(c[0]).includes("used=false"))).toBe(true),
    );
    expect(await screen.findByText("No unused sources")).toBeInTheDocument();
  });

  it("searches via the URL and renders hits with highlights", async () => {
    search = "q=ice";
    const fetchMock = mockApi((path, _init, q) => {
      if (path === "/sources/search") {
        expect(q?.get("q")).toBe("ice");
        return page([
          {
            source: makeSource({ title: "Ice Age Survival" }),
            chunk_id: "c1",
            chunk_index: 0,
            snippet: "the <mark>ice</mark> age",
            start_seconds: 61,
            end_seconds: 70,
            rank: 0.2,
          },
        ]);
      }
      return undefined;
    });
    const { container } = renderWithClient(<SourcesBrowser />);
    expect(await screen.findByRole("status")).toHaveTextContent("1 result for “ice”");
    expect(container.querySelector("mark")?.textContent).toBe("ice");
    expect(screen.getByLabelText("Position in source")).toHaveTextContent("01:01");
    expect(fetchMock.mock.calls.some((c) => String(c[0]).includes("/sources/search"))).toBe(true);
  });

  it("explains an empty search result", async () => {
    search = "q=zzz";
    mockApi((path) => (path === "/sources/search" ? page([]) : undefined));
    renderWithClient(<SourcesBrowser />);
    expect(await screen.findByText("No matches")).toBeInTheDocument();
  });

  it("submitting the search box updates the URL", async () => {
    mockApi((path) => (path === "/sources" ? page([]) : undefined));
    renderWithClient(<SourcesBrowser />);
    await screen.findByText("Your library is empty");
    fireEvent.change(screen.getByLabelText("Search transcripts"), {
      target: { value: " ice & snow " },
    });
    fireEvent.submit(screen.getByRole("search"));
    expect(replace).toHaveBeenCalledWith("/sources/videos?q=ice%20%26%20snow");
  });

  it("retries a failed source", async () => {
    const calls: string[] = [];
    mockApi((path, init) => {
      calls.push(`${init?.method ?? "GET"} ${path}`);
      if (path === "/sources")
        return page([makeSource({ id: "bad", title: "Broken", status: "failed" })]);
      if (path === "/sources/bad/retry") return { status: 202, body: { run: { id: "r" } } };
      return undefined;
    });
    renderWithClient(<SourcesBrowser />);
    fireEvent.click(await screen.findByRole("button", { name: "Retry Broken" }));
    await waitFor(() => expect(calls).toContain("POST /sources/bad/retry"));
  });
});
