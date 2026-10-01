"use client";

import { FileText, Video } from "lucide-react";
import Link from "next/link";
import { SafeSnippet } from "@/components/sources/safe-snippet";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDuration, formatTimestamp } from "@/lib/format";
import type { SearchHit, SourceListItem } from "@/lib/sources-api";

export function sourceHref(id: string): string {
  return `/sources/videos/${id}`;
}

/** True while a background import for this source is still in flight. */
export function isInFlight(s: SourceListItem): boolean {
  return (
    s.status === "importing" ||
    s.status === "discovered" ||
    s.transcript_status === "pending" ||
    s.transcript_status === "processing"
  );
}

export function needsRetry(s: SourceListItem): boolean {
  return s.status === "failed" || s.transcript_status === "failed";
}

export function KindIcon({ kind }: { kind: SourceListItem["kind"] }) {
  return kind === "youtube" ? (
    <Video className="text-muted-foreground size-4" aria-label="YouTube video" role="img" />
  ) : (
    <FileText className="text-muted-foreground size-4" aria-label="Transcript" role="img" />
  );
}

export function SourceListView({
  items,
  onRetry,
  retryingId,
}: {
  items: SourceListItem[];
  onRetry: (id: string) => void;
  retryingId?: string | null;
}) {
  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Source</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Duration</TableHead>
            <TableHead>Used</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((s) => (
            <TableRow key={s.id}>
              <TableCell>
                <div className="flex items-center gap-2">
                  <KindIcon kind={s.kind} />
                  <Link
                    className="font-medium underline-offset-4 hover:underline"
                    href={sourceHref(s.id)}
                  >
                    {s.title}
                  </Link>
                </div>
                {s.channel_title && (
                  <p className="text-muted-foreground text-xs">{s.channel_title}</p>
                )}
                {(s.error || s.transcript_error) && (
                  <p className="text-destructive text-xs">{s.error ?? s.transcript_error}</p>
                )}
              </TableCell>
              <TableCell>
                <div className="flex flex-wrap items-center gap-1">
                  <StatusBadge status={s.status} />
                  {s.transcript_status && (
                    <span className="inline-flex items-center gap-1 text-xs">
                      transcript <StatusBadge status={s.transcript_status} />
                    </span>
                  )}
                  {s.searchable && <Badge variant="secondary">searchable</Badge>}
                </div>
              </TableCell>
              <TableCell>{formatDuration(s.duration_seconds)}</TableCell>
              <TableCell>
                {s.usage_count === 0
                  ? "not used"
                  : `used in ${s.usage_count} project${s.usage_count === 1 ? "" : "s"}`}
              </TableCell>
              <TableCell className="text-right">
                {needsRetry(s) && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={retryingId === s.id}
                    onClick={() => onRetry(s.id)}
                    aria-label={`Retry ${s.title}`}
                  >
                    Retry
                  </Button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export function SearchHitView({ hit }: { hit: SearchHit }) {
  return (
    <li className="rounded-lg border p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <KindIcon kind={hit.source.kind} />
          <Link
            className="font-medium underline-offset-4 hover:underline"
            href={sourceHref(hit.source.id)}
          >
            {hit.source.title}
          </Link>
        </div>
        {hit.start_seconds !== null && (
          <span
            className="text-muted-foreground text-xs tabular-nums"
            aria-label="Position in source"
          >
            {formatTimestamp(hit.start_seconds)}
          </span>
        )}
      </div>
      <p className="text-muted-foreground mt-1 text-sm">
        <SafeSnippet snippet={hit.snippet} />
      </p>
    </li>
  );
}
