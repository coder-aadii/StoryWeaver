import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { vi } from "vitest";
import type { RunRead, SourceListItem } from "@/lib/sources-api";

export function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const result = render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
  return { client, ...result };
}

export type Reply = { status?: number; body?: unknown };

/**
 * Stub global fetch. The handler receives the request path (without /api/v1), query and init and
 * returns a body, or `{status, body}`. Unknown routes fail the test loudly.
 */
export function mockApi(
  handler: (path: string, init?: RequestInit, query?: URLSearchParams) => unknown,
) {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input));
    const path = url.pathname.replace(/^\/api\/v1/, "");
    const out = handler(path, init, url.searchParams) as Reply | undefined;
    if (out === undefined) throw new Error(`unmocked request: ${init?.method ?? "GET"} ${path}`);
    // Only `{status: <number>, body?}` is an HTTP reply; domain objects also have a string `status`.
    const isReply =
      typeof out === "object" &&
      out !== null &&
      typeof (out as Reply).status === "number" &&
      Object.keys(out).every((k) => k === "status" || k === "body");
    const status = isReply ? (out.status ?? 200) : 200;
    const body = isReply ? out.body : out;
    return new Response(status === 204 ? null : JSON.stringify(body ?? {}), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

export function makeSource(overrides: Partial<SourceListItem> = {}): SourceListItem {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    title: "Ice Age Survival",
    platform: "youtube",
    kind: "youtube",
    url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    thumbnail_url: null,
    duration_seconds: 1800,
    language: "en",
    status: "imported",
    error: null,
    channel_title: "Deep History",
    transcript_status: "ready",
    transcript_error: null,
    chunk_count: 12,
    searchable: true,
    usage_count: 0,
    created_at: "2026-10-01T10:00:00Z",
    updated_at: "2026-10-01T10:05:00Z",
    ...overrides,
  };
}

export function makeRun(overrides: Partial<RunRead> = {}): RunRead {
  return {
    id: "22222222-2222-2222-2222-222222222222",
    kind: "source.add",
    subject_type: "source_video",
    subject_id: "11111111-1111-1111-1111-111111111111",
    status: "running",
    attempt: 1,
    progress: { step: "fetching captions" },
    error: null,
    started_at: "2026-10-01T10:00:00Z",
    finished_at: null,
    created_at: "2026-10-01T10:00:00Z",
    ...overrides,
  };
}

export function page<T>(items: T[], total = items.length) {
  return { items, total, limit: 20, offset: 0 };
}
