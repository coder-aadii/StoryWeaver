"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { PageHeader } from "@/components/page-header";
import { ProjectSources } from "@/components/sources/project-sources";
import { ErrorState, LoadingRows } from "@/components/states";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, ApiError, type Project } from "@/lib/api";
import { formatDate } from "@/lib/format";

const STAGES = ["Analysis", "Script", "Storyboard", "Visuals", "Voice", "Render", "QA"];

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const { data, error, isPending } = useQuery({
    queryKey: ["/projects", id],
    queryFn: () => api<Project>(`/projects/${id}`),
    retry: (n, e) => !(e instanceof ApiError && e.status === 404) && n < 1,
  });

  if (isPending) return <LoadingRows rows={3} />;
  if (error) {
    const missing = error instanceof ApiError && error.status === 404;
    return <ErrorState message={missing ? "Project not found." : error.message} />;
  }
  return (
    <>
      <PageHeader title={data.title} description={data.description ?? undefined}>
        <StatusBadge status={data.status} />
      </PageHeader>
      <p className="text-muted-foreground mb-4 text-sm">Created {formatDate(data.created_at)}</p>
      {data.error && <ErrorState message={data.error} />}
      <div className="mb-4">
        <ProjectSources projectId={id} />
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {STAGES.map((s) => (
          <Card key={s}>
            <CardHeader>
              <CardTitle className="text-base">{s}</CardTitle>
              <CardDescription>Not implemented yet</CardDescription>
            </CardHeader>
            <CardContent />
          </Card>
        ))}
      </div>
    </>
  );
}
