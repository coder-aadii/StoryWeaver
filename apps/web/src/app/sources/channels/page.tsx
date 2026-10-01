"use client";

import { PageHeader } from "@/components/page-header";
import { ResourceList } from "@/components/resource-list";
import { StatusBadge } from "@/components/status-badge";

interface Channel {
  id: string;
  title: string;
  platform: string;
  video_count: number | null;
  status: string;
}

export default function ChannelsPage() {
  return (
    <>
      <PageHeader
        title="Channels"
        description="Channel import is planned; records can be created through the API."
      />
      <ResourceList<Channel>
        path="/channels"
        emptyTitle="No channels yet"
        emptyHint="Channel scanning and import workflows are not implemented yet."
        columns={[
          { header: "Title", cell: (r) => r.title },
          { header: "Platform", cell: (r) => r.platform },
          { header: "Videos", cell: (r) => r.video_count ?? "—" },
          { header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
        ]}
      />
    </>
  );
}
