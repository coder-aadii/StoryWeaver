"use client";

import { PageHeader } from "@/components/page-header";
import { ResourceList } from "@/components/resource-list";

interface Collection {
  id: string;
  name: string;
  description: string | null;
}

export default function CollectionsPage() {
  return (
    <>
      <PageHeader title="Collections" description="Group source videos, e.g. “History”." />
      <ResourceList<Collection>
        path="/collections"
        emptyTitle="No collections yet"
        columns={[
          { header: "Name", cell: (r) => r.name },
          { header: "Description", cell: (r) => r.description ?? "—" },
        ]}
      />
    </>
  );
}
