/**
 * TanStack Query hooks for risk intelligence data.
 */

import { useQuery } from "@tanstack/react-query";
import {
  getReportRisks,
  getCompanyRisks,
  getRiskEvolution,
  getRiskSummary,
} from "@/services/riskService";

export function useReportRisks(
  reportId: string | undefined,
  category?: string,
) {
  return useQuery({
    queryKey: ["risks", reportId, category],
    queryFn: ({ signal }) => getReportRisks(reportId!, category, signal),
    enabled: !!reportId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCompanyRisks(
  companyId: string | undefined,
  category?: string,
  severity?: string,
) {
  return useQuery({
    queryKey: ["company-risks", companyId, category, severity],
    queryFn: ({ signal }) =>
      getCompanyRisks(companyId!, category, severity, signal),
    enabled: !!companyId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useRiskEvolution(
  companyId: string | undefined,
  evolutionType?: string,
) {
  return useQuery({
    queryKey: ["risk-evolution", companyId, evolutionType],
    queryFn: ({ signal }) =>
      getRiskEvolution(companyId!, evolutionType, signal),
    enabled: !!companyId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useRiskSummary(companyId: string | undefined) {
  return useQuery({
    queryKey: ["risk-summary", companyId],
    queryFn: ({ signal }) => getRiskSummary(companyId!, signal),
    enabled: !!companyId,
    staleTime: 5 * 60 * 1000,
  });
}
