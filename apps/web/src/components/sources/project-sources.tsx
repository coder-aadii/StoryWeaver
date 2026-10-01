"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { sourceHref } from "@/components/sources/source-views";
import { ErrorState, LoadingRows } from "@/components/states";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  deleteProjectSource,
  listProjectSources,
  listSources,
  putProjectSource,
} from "@/lib/sources-api";

export function ProjectSources({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const [sourceId, setSourceId] = useState("");
  const linked = useQuery({
    queryKey: ["/projects", projectId, "sources"],
    queryFn: () => listProjectSources(projectId),
  });
  const library = useQuery({
    queryKey: ["/sources", "picker"],
    queryFn: () => listSources({ limit: 200 }),
  });
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["/projects", projectId, "sources"] });
    void queryClient.invalidateQueries({ queryKey: ["/sources"] });
  };
  const add = useMutation({
    mutationFn: () => putProjectSource(projectId, sourceId),
    onSuccess: () => {
      setSourceId("");
      refresh();
    },
  });
  const remove = useMutation({
    mutationFn: (id: string) => deleteProjectSource(projectId, id),
    onSuccess: refresh,
  });

  const linkedIds = new Set((linked.data ?? []).map((l) => l.source.id));
  const choices = (library.data?.items ?? []).filter((s) => !linkedIds.has(s.id));
  const error = linked.error ?? library.error ?? add.error ?? remove.error;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sources</CardTitle>
        <CardDescription>The library sources this project is built from.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        {linked.isPending && <LoadingRows rows={2} />}
        {error && <ErrorState message={error.message} />}
        {linked.data && linked.data.length === 0 && (
          <p className="text-muted-foreground text-sm">No sources linked yet.</p>
        )}
        {linked.data && linked.data.length > 0 && (
          <ul className="grid gap-2">
            {linked.data.map((l) => (
              <li key={l.source.id} className="flex items-center justify-between gap-2 text-sm">
                <span className="flex items-center gap-2">
                  <Link className="underline" href={sourceHref(l.source.id)}>
                    {l.source.title}
                  </Link>
                  <StatusBadge status={l.source.status} />
                  <span className="text-muted-foreground">({l.role})</span>
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => remove.mutate(l.source.id)}
                  disabled={remove.isPending}
                  aria-label={`Remove ${l.source.title}`}
                >
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        )}
        <div className="flex items-end gap-2">
          <div className="grid gap-1.5">
            <Label htmlFor="project-add-source">Add a source</Label>
            <select
              id="project-add-source"
              className="bg-background h-8 max-w-64 rounded-md border px-2 text-sm"
              value={sourceId}
              onChange={(e) => setSourceId(e.target.value)}
            >
              <option value="">Choose from your library…</option>
              {choices.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.title}
                </option>
              ))}
            </select>
          </div>
          <Button disabled={!sourceId || add.isPending} onClick={() => add.mutate()}>
            Add
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
