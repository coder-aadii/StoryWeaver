"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { PageHeader } from "@/components/page-header";
import { ResourceList } from "@/components/resource-list";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { api, type Project } from "@/lib/api";
import { formatDate } from "@/lib/format";

function NewProject() {
  const qc = useQueryClient();
  const [title, setTitle] = useState("");
  const create = useMutation({
    mutationFn: () =>
      api<Project>("/projects", { method: "POST", body: JSON.stringify({ title }) }),
    onSuccess: () => {
      setTitle("");
      return qc.invalidateQueries({ queryKey: ["/projects"] });
    },
  });
  return (
    <form
      className="flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (title.trim()) create.mutate();
      }}
    >
      <input
        aria-label="Project title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="New project title"
        className="bg-background rounded-md border px-3 text-sm"
      />
      <Button type="submit" disabled={create.isPending || !title.trim()}>
        Create
      </Button>
    </form>
  );
}

export default function ProjectsPage() {
  return (
    <>
      <PageHeader
        title="Projects"
        description="Each project turns one or more sources into a video."
      >
        <NewProject />
      </PageHeader>
      <ResourceList<Project>
        path="/projects"
        emptyTitle="No projects yet"
        emptyHint="Create one above to start."
        columns={[
          {
            header: "Title",
            cell: (r) => (
              <Link className="underline" href={`/projects/${r.id}`}>
                {r.title}
              </Link>
            ),
          },
          { header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
          { header: "Created", cell: (r) => formatDate(r.created_at) },
        ]}
      />
    </>
  );
}
