"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { api, type Ready } from "@/lib/api";

export function ApiStatus() {
  const { data, isError, isPending } = useQuery({
    queryKey: ["ready"],
    queryFn: () => api<Ready>("/health/ready"),
    refetchInterval: 15_000,
    retry: false,
  });
  if (isPending) return <Badge variant="outline">API …</Badge>;
  if (isError) return <Badge variant="destructive">API not ready</Badge>;
  return <Badge variant="secondary">API {data.status}</Badge>;
}
