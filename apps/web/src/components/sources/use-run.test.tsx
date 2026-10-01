import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { makeRun, mockApi } from "@/test/utils";
import { RUN_POLL_MS, runRefetchInterval, useRun } from "./use-run";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("runRefetchInterval", () => {
  it("keeps polling while the run is in flight and stops at terminal states", () => {
    expect(runRefetchInterval(undefined)).toBe(RUN_POLL_MS);
    expect(runRefetchInterval("queued")).toBe(RUN_POLL_MS);
    expect(runRefetchInterval("running")).toBe(RUN_POLL_MS);
    for (const s of ["succeeded", "failed", "interrupted"] as const) {
      expect(runRefetchInterval(s)).toBe(false);
    }
  });
});

describe("useRun", () => {
  let client: QueryClient;
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  beforeEach(() => {
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  });

  it("does nothing without a run id", async () => {
    const fetchMock = mockApi(() => ({}));
    renderHook(() => useRun(null), { wrapper });
    await new Promise((r) => setTimeout(r, 20));
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("polls until terminal, then stops and refreshes the source queries", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const statuses = ["running", "running", "succeeded"] as const;
    let n = 0;
    const fetchMock = mockApi((path) => {
      if (path === "/runs/r1") return makeRun({ id: "r1", status: statuses[Math.min(n++, 2)] });
      return undefined;
    });
    const invalidate = vi.spyOn(client, "invalidateQueries");

    const { result } = renderHook(() => useRun("r1"), { wrapper });
    await waitFor(() => expect(result.current.data?.status).toBe("running"));
    await vi.advanceTimersByTimeAsync(RUN_POLL_MS + 100);
    await vi.advanceTimersByTimeAsync(RUN_POLL_MS + 100);
    await waitFor(() => expect(result.current.data?.status).toBe("succeeded"));
    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ["/sources"] }));

    const callsAtTerminal = fetchMock.mock.calls.length;
    expect(callsAtTerminal).toBe(3);
    await vi.advanceTimersByTimeAsync(RUN_POLL_MS * 5);
    expect(fetchMock.mock.calls.length).toBe(callsAtTerminal); // polling stopped
  });

  it("does not poll again once the first response is already terminal", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const fetchMock = mockApi(() => makeRun({ id: "r2", status: "failed" }));
    const { result } = renderHook(() => useRun("r2"), { wrapper });
    await waitFor(() => expect(result.current.data?.status).toBe("failed"));
    await vi.advanceTimersByTimeAsync(RUN_POLL_MS * 4);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
