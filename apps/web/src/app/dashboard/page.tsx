"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { PageHeader } from "@/components/page-header";
import { ErrorState } from "@/components/states";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

const STATS = [
  { label: "Projects", path: "/projects", href: "/projects" },
  { label: "Source videos", path: "/sources", href: "/sources/videos" },
  { label: "Channels", path: "/channels", href: "/sources/channels" },
  { label: "Collections", path: "/collections", href: "/collections" },
];

function Stat({ label, path, href }: (typeof STATS)[number]) {
  const { data, isPending, isError } = useQuery({
    queryKey: [path],
    queryFn: () => api<unknown[]>(path),
  });
  return (
    <Link href={href}>
      <Card className="hover:bg-accent/40 transition-colors">
        <CardHeader>
          <CardDescription>{label}</CardDescription>
          <CardTitle className="text-3xl">
            {isPending ? <Skeleton className="h-9 w-12" /> : isError ? "—" : data.length}
          </CardTitle>
        </CardHeader>
      </Card>
    </Link>
  );
}

export default function DashboardPage() {
  const health = useQuery({
    queryKey: ["ready"],
    queryFn: () => api<{ status: string }>("/health/ready"),
    retry: false,
  });
  return (
    <>
      <PageHeader title="Dashboard" description="From source to story to video." />
      {health.isError && (
        <div className="mb-6">
          <ErrorState message="The API is unreachable or its database is not ready. Start PostgreSQL, run migrations, then start the API (see docs/development/setup.md)." />
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STATS.map((s) => (
          <Stat key={s.label} {...s} />
        ))}
      </div>
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Pipeline status</CardTitle>
          <CardDescription>
            Foundation only: data model, API, provider interfaces and a Remotion composition exist.
            Ingestion, story generation and rendering workflows are not implemented yet.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-muted-foreground text-sm">
          See the{" "}
          <Link className="underline" href="/studio">
            Studio
          </Link>{" "}
          page for the planned architecture.
        </CardContent>
      </Card>
    </>
  );
}
