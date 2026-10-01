"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { PageHeader } from "@/components/page-header";
import { AddSourceDialog } from "@/components/sources/add-source-dialog";
import { KindIcon, SearchHitView, needsRetry } from "@/components/sources/source-views";
import { useRetrySource } from "@/components/sources/use-retry";
import { useRun } from "@/components/sources/use-run";
import { EmptyState, ErrorState, LoadingRows } from "@/components/states";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError, type Project } from "@/lib/api";
import { formatDate, formatDuration, formatTimestamp } from "@/lib/format";
import {
  deleteSource,
  getSource,
  getTranscript,
  getUsage,
  putProjectSource,
  searchSources,
  type SourceDetail,
} from "@/lib/sources-api";

const SEGMENT_PAGE = 50;

/** Message for a failed delete; `source_in_use` gets an actionable hint. */
export function deleteErrorMessage(error: Error): string {
  if (error instanceof ApiError && error.code === "source_in_use") {
    return "This source is used by a project. Unlink it from its projects first, then delete it.";
  }
  return error.message;
}

function DeleteSource({ source }: { source: SourceDetail }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const del = useMutation({
    mutationFn: () => deleteSource(source.id),
    onSuccess: () => {
      setOpen(false);
      queryClient.removeQueries({ queryKey: ["/sources", source.id] });
      void queryClient.invalidateQueries({ queryKey: ["/sources"] });
      router.replace("/sources/videos");
    },
  });
  return (
    <>
      <Button variant="destructive" onClick={() => setOpen(true)}>
        Delete
      </Button>
      <Dialog
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          if (!next) del.reset();
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this source?</DialogTitle>
            <DialogDescription>
              “{source.title}” and its transcript will be removed from your library. This cannot be
              undone.
            </DialogDescription>
          </DialogHeader>
          {del.error && (
            <p role="alert" className="text-destructive text-sm">
              {deleteErrorMessage(del.error)}
            </p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" disabled={del.isPending} onClick={() => del.mutate()}>
              {del.isPending ? "Deleting…" : "Delete source"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

function FailurePanel({ source }: { source: SourceDetail }) {
  const retry = useRetrySource();
  const message = source.error ?? source.transcript_error ?? "The import did not complete.";
  return (
    <div role="alert" className="border-destructive/40 grid gap-3 rounded-lg border p-4">
      <div>
        <p className="text-destructive font-medium">Something went wrong</p>
        <p className="text-sm">{message}</p>
        {retry.error && <p className="text-destructive text-sm">{retry.error.message}</p>}
      </div>
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => retry.mutate(source.id)} disabled={retry.isPending}>
          {retry.isPending ? "Retrying…" : "Retry"}
        </Button>
        <AddSourceDialog
          attachToSourceId={source.id}
          label="Upload transcript instead"
          variant="outline"
        />
      </div>
    </div>
  );
}

function TranscriptViewer({ source }: { source: SourceDetail }) {
  const [offset, setOffset] = useState(0);
  const ready = source.transcript?.status === "ready";
  const content = useQuery({
    queryKey: ["/sources", source.id, "transcript", offset],
    queryFn: () => getTranscript(source.id, { limit: SEGMENT_PAGE, offset }),
    enabled: ready,
    placeholderData: keepPreviousData,
  });
  if (!ready) return null;
  if (content.isPending) return <LoadingRows rows={3} />;
  if (content.error) return <ErrorState message={content.error.message} />;
  const seg = content.data.segments;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Transcript</CardTitle>
        <CardDescription>
          v{content.data.transcript.version} · {content.data.transcript.origin} ·{" "}
          {content.data.transcript.segment_count} segments
          {content.data.transcript.timed ? "" : " · no timestamps (plain text)"}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        <ol className="grid gap-2">
          {seg.items.map((s, i) => (
            <li key={seg.offset + i} className="flex gap-3 text-sm">
              {content.data.transcript.timed && (
                <span className="text-muted-foreground w-14 shrink-0 tabular-nums">
                  {formatTimestamp(s.start)}
                </span>
              )}
              <span>{s.text}</span>
            </li>
          ))}
        </ol>
        {seg.total > SEGMENT_PAGE && (
          <div className="flex items-center justify-between text-sm">
            <Button
              variant="outline"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - SEGMENT_PAGE))}
            >
              Previous
            </Button>
            <span className="text-muted-foreground">
              {offset + 1}–{Math.min(offset + SEGMENT_PAGE, seg.total)} of {seg.total}
            </span>
            <Button
              variant="outline"
              disabled={offset + SEGMENT_PAGE >= seg.total}
              onClick={() => setOffset(offset + SEGMENT_PAGE)}
            >
              Next
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function InSourceSearch({ source }: { source: SourceDetail }) {
  const [draft, setDraft] = useState("");
  const [q, setQ] = useState("");
  const search = useQuery({
    queryKey: ["/sources", source.id, "search", q],
    queryFn: () => searchSources({ q, source_id: source.id, limit: 20 }),
    enabled: Boolean(q) && source.searchable,
  });
  const hits = search.data?.items ?? [];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Search in this source</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        {!source.searchable ? (
          <p className="text-muted-foreground text-sm">
            Not searchable until a transcript is ready.
          </p>
        ) : (
          <form
            role="search"
            className="flex items-end gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              setQ(draft.trim());
            }}
          >
            <div className="grid gap-1.5">
              <Label htmlFor="in-source-search">Word or phrase</Label>
              <Input
                id="in-source-search"
                value={draft}
                maxLength={200}
                onChange={(e) => setDraft(e.target.value)}
              />
            </div>
            <Button type="submit" variant="outline">
              <Search aria-hidden /> Search
            </Button>
          </form>
        )}
        {search.error && <ErrorState message={search.error.message} />}
        {q &&
          search.data &&
          (hits.length === 0 ? (
            <p className="text-muted-foreground text-sm">No matches in this source.</p>
          ) : (
            <ul className="grid gap-2" aria-label="Matches in this source">
              {hits.map((h) => (
                <SearchHitView key={h.chunk_id} hit={h} />
              ))}
            </ul>
          ))}
      </CardContent>
    </Card>
  );
}

function UsagePanel({ source }: { source: SourceDetail }) {
  const queryClient = useQueryClient();
  const [projectId, setProjectId] = useState("");
  const usage = useQuery({
    queryKey: ["/sources", source.id, "usage"],
    queryFn: () => getUsage(source.id),
  });
  const projects = useQuery({
    queryKey: ["/projects"],
    queryFn: () => api<Project[]>("/projects"),
  });
  const link = useMutation({
    mutationFn: () => putProjectSource(projectId, source.id),
    onSuccess: () => {
      setProjectId("");
      void queryClient.invalidateQueries({ queryKey: ["/sources"] });
      void queryClient.invalidateQueries({ queryKey: ["/projects"] });
    },
  });
  const linked = new Set((usage.data ?? []).map((u) => u.project_id));
  const choices = (projects.data ?? []).filter((p) => !linked.has(p.id));
  return (
    <Card>
      <CardHeader>
        <CardTitle>Used in projects</CardTitle>
        <CardDescription>
          Usage is tracked per project (not per idea) in this release.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        {usage.error && <ErrorState message={usage.error.message} />}
        {usage.data && usage.data.length === 0 && (
          <p className="text-muted-foreground text-sm">Not used by any project yet.</p>
        )}
        {usage.data && usage.data.length > 0 && (
          <ul className="grid gap-1 text-sm">
            {usage.data.map((u) => (
              <li key={u.project_id}>
                <Link className="underline" href={`/projects/${u.project_id}`}>
                  {u.project_title}
                </Link>{" "}
                <span className="text-muted-foreground">({u.role})</span>
              </li>
            ))}
          </ul>
        )}
        <div className="flex items-end gap-2">
          <div className="grid gap-1.5">
            <Label htmlFor="add-to-project">Add to project</Label>
            <select
              id="add-to-project"
              className="bg-background h-8 rounded-md border px-2 text-sm"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
            >
              <option value="">Choose a project…</option>
              {choices.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))}
            </select>
          </div>
          <Button disabled={!projectId || link.isPending} onClick={() => link.mutate()}>
            Add
          </Button>
        </div>
        {link.error && <ErrorState message={link.error.message} />}
      </CardContent>
    </Card>
  );
}

export function SourceDetailView({ id }: { id: string }) {
  const source = useQuery({
    queryKey: ["/sources", id],
    queryFn: () => getSource(id),
    retry: (n, e) => !(e instanceof ApiError && e.status === 404) && n < 1,
    refetchInterval: (q) => (q.state.data?.active_run ? 2000 : false),
  });
  // Poll the active run; the hook refreshes source queries once it finishes.
  useRun(source.data?.active_run?.id);

  if (source.isPending) return <LoadingRows rows={3} />;
  if (source.error) {
    const missing = source.error instanceof ApiError && source.error.status === 404;
    return <ErrorState message={missing ? "Source not found." : source.error.message} />;
  }
  const s = source.data;
  return (
    <>
      <PageHeader title={s.title} description={s.channel_title ?? undefined}>
        <div className="flex items-center gap-2">
          <KindIcon kind={s.kind} />
          <StatusBadge status={s.status} />
          {s.searchable && <Badge variant="secondary">searchable</Badge>}
          <DeleteSource source={s} />
        </div>
      </PageHeader>

      <div className="grid gap-4">
        {needsRetry(s) && <FailurePanel source={s} />}
        {s.active_run && (
          <p role="status" className="text-muted-foreground text-sm">
            Import {s.active_run.status}
            {typeof s.active_run.progress?.step === "string"
              ? ` (${s.active_run.progress.step})`
              : ""}
            …
          </p>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-[auto_1fr]">
            {s.thumbnail_url && (
              // eslint-disable-next-line @next/next/no-img-element -- remote thumbnail; not proxied or optimised
              <img
                src={s.thumbnail_url}
                alt={`Thumbnail of ${s.title}`}
                referrerPolicy="no-referrer"
                loading="lazy"
                className="h-24 rounded-md border object-cover"
              />
            )}
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
              <dt className="text-muted-foreground">Platform</dt>
              <dd>{s.platform}</dd>
              <dt className="text-muted-foreground">Duration</dt>
              <dd>{formatDuration(s.duration_seconds)}</dd>
              <dt className="text-muted-foreground">Language</dt>
              <dd>{s.language ?? "—"}</dd>
              <dt className="text-muted-foreground">Added</dt>
              <dd>{formatDate(s.created_at)}</dd>
              {s.url && (
                <>
                  <dt className="text-muted-foreground">Origin</dt>
                  <dd>
                    <a className="underline" href={s.url} target="_blank" rel="noopener noreferrer">
                      Open original
                    </a>
                  </dd>
                </>
              )}
              {s.description && (
                <>
                  <dt className="text-muted-foreground">Description</dt>
                  <dd className="whitespace-pre-line">{s.description}</dd>
                </>
              )}
            </dl>
          </CardContent>
        </Card>

        {!s.transcript && !s.active_run && !needsRetry(s) && (
          <EmptyState title="No transcript yet" hint="Retry the import or upload a transcript." />
        )}
        <TranscriptViewer source={s} />
        <InSourceSearch source={s} />
        <UsagePanel source={s} />
      </div>
    </>
  );
}
