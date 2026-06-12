/**
 * TanStack Query hooks for financial data (metrics, comparisons, analytics).
 */

import { useQuery } from "@tanstack/react-query";
import {
  getMetrics,
  getMetricsSummary,
  getReportComparisons,
  getCompanyComparisons,
  getCompanyComparisonSummary,
  getReportAnalytics,
  getCompanyAnalytics,
  getCompanyAnalyticsSummary,
} from "@/services/financialService";

export function useMetrics(reportId: string | undefined, category?: string) {
  return useQuery({
    queryKey: ["metrics", reportId, category],
    queryFn: ({ signal }) => getMetrics(reportId!, category, signal),
    enabled: !!reportId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useMetricsSummary(reportId: string | undefined) {
  return useQuery({
    queryKey: ["metrics-summary", reportId],
    queryFn: ({ signal }) => getMetricsSummary(reportId!, signal),
    enabled: !!reportId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useReportComparisons(reportId: string | undefined) {
  return useQuery({
    queryKey: ["comparisons", reportId],
    queryFn: ({ signal }) => getReportComparisons(reportId!, signal),
    enabled: !!reportId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCompanyComparisons(
  companyId: string | undefined,
  comparisonType?: string,
) {
  return useQuery({
    queryKey: ["company-comparisons", companyId, comparisonType],
    queryFn: ({ signal }) =>
      getCompanyComparisons(companyId!, comparisonType, signal),
    enabled: !!companyId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCompanyComparisonSummary(companyId: string | undefined) {
  return useQuery({
    queryKey: ["company-comparison-summary", companyId],
    queryFn: ({ signal }) => getCompanyComparisonSummary(companyId!, signal),
    enabled: !!companyId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useReportAnalytics(reportId: string | undefined) {
  return useQuery({
    queryKey: ["analytics", reportId],
    queryFn: ({ signal }) => getReportAnalytics(reportId!, signal),
    enabled: !!reportId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCompanyAnalytics(
  companyId: string | undefined,
  signalType?: string,
) {
  return useQuery({
    queryKey: ["company-analytics", companyId, signalType],
    queryFn: ({ signal }) =>
      getCompanyAnalytics(companyId!, signalType, signal),
    enabled: !!companyId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCompanyAnalyticsSummary(companyId: string | undefined) {
  return useQuery({
    queryKey: ["company-analytics-summary", companyId],
    queryFn: ({ signal }) => getCompanyAnalyticsSummary(companyId!, signal),
    enabled: !!companyId,
    staleTime: 5 * 60 * 1000,
  });
}
