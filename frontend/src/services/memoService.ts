/**
 * Memo service — generation, details, citations, export.
 */

import { get, post } from "./api";
import type {
  MemoDetails,
  MemoGenerationResponse,
  MemoExportResponse,
  Citation,
} from "@/types/api";

export interface MemoGeneratePayload {
  company_id: string;
  report_id: string;
  benchmark_run_id?: string;
  memo_type?: string;
  title?: string;
}

export function generateMemo(
  payload: MemoGeneratePayload,
  signal?: AbortSignal,
): Promise<MemoGenerationResponse> {
  return post<MemoGenerationResponse>("/memos", payload, signal);
}

export function getMemoDetails(
  memoId: string,
  signal?: AbortSignal,
): Promise<MemoDetails> {
  return get<MemoDetails>(`/memos/${memoId}`, signal);
}

export function getMemoCitations(
  memoId: string,
  signal?: AbortSignal,
): Promise<Citation[]> {
  return get<Citation[]>(`/memos/${memoId}/citations`, signal);
}

export function exportMemo(
  memoId: string,
  format: "markdown" | "json" = "markdown",
  signal?: AbortSignal,
): Promise<MemoExportResponse> {
  return get<MemoExportResponse>(
    `/memos/${memoId}/export?format=${format}`,
    signal,
  );
}
