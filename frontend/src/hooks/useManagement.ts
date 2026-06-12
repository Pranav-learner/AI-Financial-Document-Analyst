/**
 * TanStack Query hooks for management tone data.
 */

import { useQuery } from "@tanstack/react-query";
import {
  getReportTone,
  getCompanyTone,
  getToneEvolution,
  getToneSummary,
} from "@/services/managementService";

export function useReportTone(reportId: string | undefined) {
  return useQuery({
    queryKey: ["tone", reportId],
    queryFn: ({ signal }) => getReportTone(reportId!, signal),
    enabled: !!reportId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCompanyTone(companyId: string | undefined) {
  return useQuery({
    queryKey: ["company-tone", companyId],
    queryFn: ({ signal }) => getCompanyTone(companyId!, signal),
    enabled: !!companyId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useToneEvolution(companyId: string | undefined) {
  return useQuery({
    queryKey: ["tone-evolution", companyId],
    queryFn: ({ signal }) => getToneEvolution(companyId!, signal),
    enabled: !!companyId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useToneSummary(companyId: string | undefined) {
  return useQuery({
    queryKey: ["tone-summary", companyId],
    queryFn: ({ signal }) => getToneSummary(companyId!, signal),
    enabled: !!companyId,
    staleTime: 5 * 60 * 1000,
  });
}
