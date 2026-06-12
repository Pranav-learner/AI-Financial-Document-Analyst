/**
 * TanStack Query hooks for benchmark data.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getBenchmarkRun,
  getBenchmarkResults,
  getBenchmarkSummary,
  createBenchmarkRun,
  compareCohort,
} from "@/services/benchmarkService";
import type { BenchmarkRunCreatePayload, BenchmarkComparePayload } from "@/services/benchmarkService";

export function useBenchmarkRun(runId: string | undefined) {
  return useQuery({
    queryKey: ["benchmark-run", runId],
    queryFn: ({ signal }) => getBenchmarkRun(runId!, signal),
    enabled: !!runId,
    staleTime: 30 * 1000, // 30s — runs may still be processing
  });
}

export function useBenchmarkResults(runId: string | undefined) {
  return useQuery({
    queryKey: ["benchmark-results", runId],
    queryFn: ({ signal }) => getBenchmarkResults(runId!, signal),
    enabled: !!runId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useBenchmarkSummary(runId: string | undefined) {
  return useQuery({
    queryKey: ["benchmark-summary", runId],
    queryFn: ({ signal }) => getBenchmarkSummary(runId!, signal),
    enabled: !!runId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateBenchmarkRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: BenchmarkRunCreatePayload) =>
      createBenchmarkRun(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["benchmark-run"] });
    },
  });
}

export function useCompareCohort() {
  return useMutation({
    mutationFn: (payload: BenchmarkComparePayload) => compareCohort(payload),
  });
}
