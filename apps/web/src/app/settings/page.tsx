"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/page-header";
import { ErrorState, LoadingRows } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type ProviderHealth } from "@/lib/api";

function Row({ label, ok }: { label: string; ok: boolean }) {
  return (
    <li className="flex items-center justify-between py-1.5 text-sm">
      <span>{label}</span>
      <Badge variant={ok ? "default" : "outline"}>{ok ? "configured" : "not configured"}</Badge>
    </li>
  );
}

export default function SettingsPage() {
  const { data, error, isPending } = useQuery({
    queryKey: ["providers"],
    queryFn: () => api<ProviderHealth>("/health/providers"),
  });
  return (
    <>
      <PageHeader
        title="Settings"
        description="Provider status. Keys live in the server's .env and are never sent to the browser."
      />
      {isPending && <LoadingRows rows={3} />}
      {error && <ErrorState message={error.message} />}
      {data && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>LLM providers</CardTitle>
              <CardDescription>
                Default: {data.default_llm_provider}
                {data.default_llm_model_set ? "" : " (no model selected)"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="divide-y">
                {Object.entries(data.llm).map(([name, ok]) => (
                  <Row key={name} label={name} ok={ok} />
                ))}
              </ul>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Local services</CardTitle>
              <CardDescription>All optional — the app boots without them.</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="divide-y">
                <Row label="Ollama reachable" ok={data.ollama_reachable} />
                <Row label="ComfyUI reachable" ok={data.comfyui.reachable} />
                <Row label="Temporal" ok={data.temporal_configured} />
              </ul>
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}
