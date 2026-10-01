"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { getRun, TERMINAL_RUN_STATUSES, type RunStatus } from "@/lib/sources-api";

export const RUN_POLL_MS = 1500;

/** Polling interval for a run: keep polling until it reaches a terminal status. */
export function runRefetchInterval(status: RunStatus | undefined): number | false {
  return status && TERMINAL_RUN_STATUSES.has(status) ? false : RUN_POLL_MS;
}

/**
 * Poll a workflow run until it is terminal, then refresh everything derived from sources.
 * Pass null/undefined when there is no run (the query stays disabled).
 */
export function useRun(runId: string | null | undefined) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["/runs", runId],
    queryFn: () => getRun(runId as string),
    enabled: Boolean(runId),
    refetchInterval: (q) => runRefetchInterval(q.state.data?.status),
  });
  const status = query.data?.status;
  useEffect(() => {
    if (status && TERMINAL_RUN_STATUSES.has(status)) {
      void queryClient.invalidateQueries({ queryKey: ["/sources"] });
    }
  }, [status, queryClient]);
  return query;
}
