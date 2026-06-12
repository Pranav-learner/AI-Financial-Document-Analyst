/**
 * Benchmark service — runs, results, summaries, cohort comparison.
 */

import { get, post } from "./api";
import type {
  BenchmarkRun,
  BenchmarkResult,
  BenchmarkSummary,
  BenchmarkComparisonResponse,
} from "@/types/api";

export interface BenchmarkRunCreatePayload {
  run_name: string;
  company_ids: string[];
  benchmark_type?: string;
  configuration?: Record<string, unknown>;
}

export interface BenchmarkComparePayload {
  company_ids: string[];
  configuration?: Record<string, unknown>;
}

export function createBenchmarkRun(
  payload: BenchmarkRunCreatePayload,
  signal?: AbortSignal,
): Promise<BenchmarkRun> {
  return post<BenchmarkRun>("/benchmark/run", payload, signal);
}

export function getBenchmarkRun(
  runId: string,
  signal?: AbortSignal,
): Promise<BenchmarkRun> {
  return get<BenchmarkRun>(`/benchmark/${runId}`, signal);
}

export function getBenchmarkResults(
  runId: string,
  signal?: AbortSignal,
): Promise<BenchmarkResult[]> {
  return get<BenchmarkResult[]>(`/benchmark/${runId}/results`, signal);
}

export function getBenchmarkSummary(
  runId: string,
  signal?: AbortSignal,
): Promise<BenchmarkSummary[]> {
  return get<BenchmarkSummary[]>(`/benchmark/${runId}/summary`, signal);
}

export function compareCohort(
  payload: BenchmarkComparePayload,
  signal?: AbortSignal,
): Promise<BenchmarkComparisonResponse> {
  return post<BenchmarkComparisonResponse>(
    "/benchmark/compare",
    payload,
    signal,
  );
}
