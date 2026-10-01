import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { makeSource, mockApi, page, renderWithClient } from "@/test/utils";
import { ProjectSources } from "./project-sources";

afterEach(() => vi.unstubAllGlobals());

const link = (id: string, title: string) => ({
  source: makeSource({ id, title }),
  role: "primary",
  linked_at: "2026-10-01T00:00:00Z",
});

describe("ProjectSources", () => {
  it("shows an empty state, then lists linked sources", async () => {
    mockApi((path) => {
      if (path === "/projects/p1/sources") return [];
      if (path === "/sources") return page([]);
      return undefined;
    });
    renderWithClient(<ProjectSources projectId="p1" />);
    expect(await screen.findByText("No sources linked yet.")).toBeInTheDocument();
  });

  it("removes a link and only offers unlinked sources in the picker", async () => {
    const calls: string[] = [];
    mockApi((path, init) => {
      calls.push(`${init?.method ?? "GET"} ${path}`);
      if (path === "/projects/p1/sources" && !init?.method) return [link("a", "Ice Age")];
      if (path === "/sources")
        return page([
          makeSource({ id: "a", title: "Ice Age" }),
          makeSource({ id: "b", title: "Cave Art" }),
        ]);
      if (path === "/projects/p1/sources/a") return { status: 204 };
      if (path === "/projects/p1/sources/b") return { status: 200, body: link("b", "Cave Art") };
      return undefined;
    });
    renderWithClient(<ProjectSources projectId="p1" />);
    expect(await screen.findByRole("link", { name: "Ice Age" })).toHaveAttribute(
      "href",
      "/sources/videos/a",
    );
    const picker = await screen.findByLabelText("Add a source");
    await waitFor(() =>
      expect(within(picker).getByRole("option", { name: "Cave Art" })).toBeInTheDocument(),
    );
    expect(within(picker).queryByRole("option", { name: "Ice Age" })).toBeNull();

    fireEvent.change(picker, { target: { value: "b" } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));
    await waitFor(() => expect(calls).toContain("PUT /projects/p1/sources/b"));

    fireEvent.click(screen.getByRole("button", { name: "Remove Ice Age" }));
    await waitFor(() => expect(calls).toContain("DELETE /projects/p1/sources/a"));
  });

  it("surfaces API errors", async () => {
    mockApi((path) => {
      if (path === "/projects/p1/sources")
        return { status: 404, body: { detail: "projects not found", code: "not_found" } };
      if (path === "/sources") return page([]);
      return undefined;
    });
    renderWithClient(<ProjectSources projectId="p1" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("projects not found");
  });
});
