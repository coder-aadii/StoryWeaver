"use client";

import { PageHeader } from "@/components/page-header";
import { ResourceList } from "@/components/resource-list";
import { StatusBadge } from "@/components/status-badge";

interface SourceVideo {
  id: string;
  title: string;
  platform: string;
  duration_seconds: number | null;
  status: string;
}

export default function VideosPage() {
  return (
    <>
      <PageHeader title="Videos" description="Source videos available to projects." />
      <ResourceList<SourceVideo>
        path="/sources"
        emptyTitle="No source videos yet"
        emptyHint="Ingestion workflows are not implemented yet."
        columns={[
          { header: "Title", cell: (r) => r.title },
          { header: "Platform", cell: (r) => r.platform },
          {
            header: "Duration",
            cell: (r) => (r.duration_seconds ? `${Math.round(r.duration_seconds / 60)} min` : "—"),
          },
          { header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
        ]}
      />
    </>
  );
}
