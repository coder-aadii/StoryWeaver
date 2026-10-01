"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { retrySource } from "@/lib/sources-api";

/** Retry a failed import; refreshes source queries so the list shows the new in-flight state. */
export function useRetrySource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sourceId: string) => retrySource(sourceId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["/sources"] }),
  });
}
