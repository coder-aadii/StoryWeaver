"use client";

import { PageHeader } from "@/components/page-header";
import { ResourceList } from "@/components/resource-list";

interface Topic {
  id: string;
  name: string;
  slug: string;
  description: string | null;
}

export default function TopicsPage() {
  return (
    <>
      <PageHeader title="Topics" description="Themes detected across your sources." />
      <ResourceList<Topic>
        path="/topics"
        emptyTitle="No topics yet"
        emptyHint="Automatic topic classification is planned."
        columns={[
          { header: "Name", cell: (r) => r.name },
          { header: "Slug", cell: (r) => r.slug },
          { header: "Description", cell: (r) => r.description ?? "—" },
        ]}
      />
    </>
  );
}
