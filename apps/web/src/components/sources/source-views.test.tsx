import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { makeSource } from "@/test/utils";
import { SearchHitView, SourceListView, isInFlight, needsRetry } from "./source-views";

describe("SourceListView", () => {
  it("renders statuses, duration, usage and the searchable badge", () => {
    render(
      <SourceListView
        items={[
          makeSource({
            id: "a",
            title: "Ice Age Survival",
            usage_count: 2,
            duration_seconds: 1800,
          }),
          makeSource({
            id: "b",
            title: "Cave Art",
            usage_count: 0,
            searchable: false,
            transcript_status: "pending",
          }),
        ]}
        onRetry={vi.fn()}
      />,
    );
    const row = screen.getByRole("row", { name: /Ice Age Survival/ });
    expect(within(row).getByText("imported")).toBeInTheDocument();
    expect(within(row).getByText("searchable")).toBeInTheDocument();
    expect(within(row).getByText("30 min")).toBeInTheDocument();
    expect(within(row).getByText("used in 2 projects")).toBeInTheDocument();
    expect(within(row).getByRole("link", { name: "Ice Age Survival" })).toHaveAttribute(
      "href",
      "/sources/videos/a",
    );
    const other = screen.getByRole("row", { name: /Cave Art/ });
    expect(within(other).getByText("not used")).toBeInTheDocument();
    expect(within(other).queryByText("searchable")).toBeNull();
    expect(screen.queryAllByRole("button", { name: /Retry/ })).toHaveLength(0);
  });

  it("offers Retry only for failed sources/transcripts and calls back with the id", () => {
    const onRetry = vi.fn();
    render(
      <SourceListView
        items={[
          makeSource({ id: "ok", title: "Fine" }),
          makeSource({ id: "bad", title: "Broken", status: "failed", error: "video unavailable" }),
          makeSource({
            id: "nocap",
            title: "No captions",
            transcript_status: "failed",
            transcript_error: "no captions",
            searchable: false,
          }),
        ]}
        onRetry={onRetry}
      />,
    );
    expect(screen.queryByRole("button", { name: "Retry Fine" })).toBeNull();
    expect(screen.getByText("video unavailable")).toBeInTheDocument();
    expect(screen.getByText("no captions")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry Broken" }));
    expect(onRetry).toHaveBeenCalledWith("bad");
    expect(screen.getByRole("button", { name: "Retry No captions" })).toBeInTheDocument();
  });

  it("disables the Retry button of the row being retried", () => {
    render(
      <SourceListView
        items={[makeSource({ id: "bad", title: "Broken", status: "failed" })]}
        onRetry={vi.fn()}
        retryingId="bad"
      />,
    );
    expect(screen.getByRole("button", { name: "Retry Broken" })).toBeDisabled();
  });
});

describe("helpers", () => {
  it("classifies in-flight and retryable sources", () => {
    expect(isInFlight(makeSource({ status: "importing" }))).toBe(true);
    expect(isInFlight(makeSource({ transcript_status: "processing" }))).toBe(true);
    expect(isInFlight(makeSource())).toBe(false);
    expect(needsRetry(makeSource({ status: "failed" }))).toBe(true);
    expect(needsRetry(makeSource({ transcript_status: "failed" }))).toBe(true);
    expect(needsRetry(makeSource())).toBe(false);
  });
});

describe("SearchHitView", () => {
  const hit = (over = {}) => ({
    source: makeSource({ id: "s1", title: "Ice Age Survival" }),
    chunk_id: "c1",
    chunk_index: 3,
    snippet: "they crossed the <mark>ice</mark> &amp; snow",
    start_seconds: 125,
    end_seconds: 140,
    rank: 0.4,
    ...over,
  });

  it("shows the title link, highlighted snippet and mm:ss position", () => {
    const { container } = render(
      <ul>
        <SearchHitView hit={hit()} />
      </ul>,
    );
    expect(screen.getByRole("link", { name: "Ice Age Survival" })).toHaveAttribute(
      "href",
      "/sources/videos/s1",
    );
    expect(container.querySelector("mark")?.textContent).toBe("ice");
    expect(screen.getByText(/they crossed the/)).toHaveTextContent("they crossed the ice & snow");
    expect(screen.getByLabelText("Position in source")).toHaveTextContent("02:05");
  });

  it("omits the position for untimed transcripts", () => {
    render(
      <ul>
        <SearchHitView hit={hit({ start_seconds: null, end_seconds: null })} />
      </ul>,
    );
    expect(screen.queryByLabelText("Position in source")).toBeNull();
  });

  it("never turns hostile snippet markup into elements", () => {
    const { container } = render(
      <ul>
        <SearchHitView
          hit={hit({
            snippet: '<img src=x onerror="alert(1)"><script>alert(2)</script> <mark>ok</mark>',
          })}
        />
      </ul>,
    );
    expect(container.querySelector("img, script")).toBeNull();
    expect(container.querySelectorAll("mark")).toHaveLength(1);
  });
});
