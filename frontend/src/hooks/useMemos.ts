/**
 * TanStack Query hooks for investment memos.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getMemoDetails,
  getMemoCitations,
  exportMemo,
  generateMemo,
} from "@/services/memoService";
import type { MemoGeneratePayload } from "@/services/memoService";

export function useMemoDetails(memoId: string | undefined) {
  return useQuery({
    queryKey: ["memo", memoId],
    queryFn: ({ signal }) => getMemoDetails(memoId!, signal),
    enabled: !!memoId,
    staleTime: 30 * 1000,
  });
}

export function useMemoCitations(memoId: string | undefined) {
  return useQuery({
    queryKey: ["memo-citations", memoId],
    queryFn: ({ signal }) => getMemoCitations(memoId!, signal),
    enabled: !!memoId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useMemoExport(
  memoId: string | undefined,
  format: "markdown" | "json" = "markdown",
  enabled = false,
) {
  return useQuery({
    queryKey: ["memo-export", memoId, format],
    queryFn: ({ signal }) => exportMemo(memoId!, format, signal),
    enabled: enabled && !!memoId,
  });
}

export function useGenerateMemo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: MemoGeneratePayload) => generateMemo(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["memo"] });
    },
  });
}
