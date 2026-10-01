"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { AddSourceDialog } from "@/components/sources/add-source-dialog";
import { SearchHitView, SourceListView, isInFlight } from "@/components/sources/source-views";
import { useRetrySource } from "@/components/sources/use-retry";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { listSources, searchSources } from "@/lib/sources-api";

const PAGE_SIZE = 20;

export function SourcesBrowser() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const q = (params.get("q") ?? "").trim();
  const [draft, setDraft] = useState(q);
  const [excludeUsed, setExcludeUsed] = useState(false);
  // The page offset belongs to one (query, filter) combination; a different one starts at 0.
  // Deriving it avoids resetting state in an effect.
  const pageKey = `${q}|${excludeUsed}`;
  const [pageState, setPageState] = useState({ key: pageKey, offset: 0 });
  const offset = pageState.key === pageKey ? pageState.offset : 0;
  const setOffset = (next: number) => setPageState({ key: pageKey, offset: next });
  const retry = useRetrySource();
  // Keep the input in sync when the URL query changes (back/forward, "Clear").
  const [syncedQ, setSyncedQ] = useState(q);
  if (syncedQ !== q) {
    setSyncedQ(q);
    setDraft(q);
  }

  const list = useQuery({
    queryKey: ["/sources", "list", { excludeUsed, offset }],
    queryFn: () => listSources({ limit: PAGE_SIZE, offset, used: excludeUsed ? false : undefined }),
    enabled: !q,
    placeholderData: keepPreviousData,
    // While an import is in flight, keep the list fresh.
    refetchInterval: (query) => (query.state.data?.items.some(isInFlight) ? 3000 : false),
  });
  const search = useQuery({
    queryKey: ["/sources", "search", { q, excludeUsed, offset }],
    queryFn: () =>
      searchSources({ q, exclude_used: excludeUsed || undefined, limit: PAGE_SIZE, offset }),
    enabled: Boolean(q),
    placeholderData: keepPreviousData,
  });

  function submitSearch(e: React.FormEvent) {
    e.preventDefault();
    const next = draft.trim();
    router.replace(next ? `${pathname}?q=${encodeURIComponent(next)}` : pathname);
  }

  const active = q ? search : list;
  const total = active.data?.total ?? 0;

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <form onSubmit={submitSearch} className="flex items-end gap-2" role="search">
          <div className="grid gap-1.5">
            <Label htmlFor="source-search">Search transcripts</Label>
            <Input
              id="source-search"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="a word or phrase"
              maxLength={200}
              className="w-64"
            />
          </div>
          <Button type="submit" variant="outline">
            <Search aria-hidden /> Search
          </Button>
          {q && (
            <Button type="button" variant="ghost" onClick={() => router.replace(pathname)}>
              Clear
            </Button>
          )}
        </form>
        <AddSourceDialog />
      </div>

      <div className="flex items-center gap-2">
        <input
          id="exclude-used"
          type="checkbox"
          checked={excludeUsed}
          onChange={(e) => setExcludeUsed(e.target.checked)}
        />
        <Label htmlFor="exclude-used">Hide sources already used in a project</Label>
      </div>

      {active.isPending && <LoadingRows />}
      {active.error && <ErrorState message={active.error.message} />}
      {retry.error && <ErrorState message={retry.error.message} />}

      {!q && list.data && list.data.items.length === 0 && (
        <EmptyState
          title={excludeUsed ? "No unused sources" : "Your library is empty"}
          hint={
            excludeUsed
              ? "Every source is already linked to a project."
              : "Add a YouTube video URL (metadata and captions are fetched; no video is downloaded) or upload a transcript (.txt, .srt, .vtt) or paste text."
          }
        />
      )}
      {!q && list.data && list.data.items.length > 0 && (
        <SourceListView
          items={list.data.items}
          onRetry={(id) => retry.mutate(id)}
          retryingId={retry.isPending ? retry.variables : null}
        />
      )}

      {q && search.data && (
        <>
          <p className="text-muted-foreground text-sm" role="status">
            {search.data.total} result{search.data.total === 1 ? "" : "s"} for “{q}”
          </p>
          {search.data.items.length === 0 ? (
            <EmptyState
              title="No matches"
              hint="Only sources whose transcript is ready are searchable. Try a different word."
            />
          ) : (
            <ul className="grid gap-2" aria-label="Search results">
              {search.data.items.map((hit) => (
                <SearchHitView key={hit.chunk_id} hit={hit} />
              ))}
            </ul>
          )}
        </>
      )}

      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between text-sm">
          <Button
            variant="outline"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          >
            Previous
          </Button>
          <span className="text-muted-foreground">
            {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
          </span>
          <Button
            variant="outline"
            disabled={offset + PAGE_SIZE >= total}
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
