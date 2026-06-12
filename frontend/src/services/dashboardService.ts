/**
 * Dashboard aggregate service — fetches cross-cutting data for the executive overview.
 */

import { get } from "./api";
import type { ReportListResponse } from "@/types/api";

export function getReports(
  limit = 20,
  offset = 0,
  signal?: AbortSignal,
): Promise<ReportListResponse> {
  return get<ReportListResponse>(
    `/reports?limit=${limit}&offset=${offset}`,
    signal,
  );
}
