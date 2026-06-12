/**
 * TanStack Query hooks for report data.
 */

import { useQuery } from "@tanstack/react-query";
import { getReports } from "@/services/dashboardService";
import type { ReportListResponse } from "@/types/api";

export function useReports(limit = 20, offset = 0) {
  return useQuery<ReportListResponse>({
    queryKey: ["reports", limit, offset],
    queryFn: ({ signal }) => getReports(limit, offset, signal),
    staleTime: 5 * 60 * 1000,
  });
}
