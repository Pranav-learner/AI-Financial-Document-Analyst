/**
 * Financial service — metrics, comparisons, analytics APIs.
 */

import { get } from "./api";
import type {
  MetricListResponse,
  MetricSummaryResponse,
  ComparisonListResponse,
  ComparisonSummaryResponse,
  AnalyticsListResponse,
  AnalyticsSummaryResponse,
  FinancialMetric,
} from "@/types/api";

// ─── Metrics (Phase 3A) ─────────────────────────────────────────────────────

export function getMetrics(
  reportId: string,
  category?: string,
  signal?: AbortSignal,
): Promise<MetricListResponse> {
  const params = category ? `?category=${encodeURIComponent(category)}` : "";
  return get<MetricListResponse>(
    `/reports/${reportId}/metrics${params}`,
    signal,
  );
}

export function getMetric(
  reportId: string,
  metricId: string,
  signal?: AbortSignal,
): Promise<FinancialMetric> {
  return get<FinancialMetric>(
    `/reports/${reportId}/metrics/${metricId}`,
    signal,
  );
}

export function getMetricsSummary(
  reportId: string,
  signal?: AbortSignal,
): Promise<MetricSummaryResponse> {
  return get<MetricSummaryResponse>(
    `/reports/${reportId}/metrics/summary`,
    signal,
  );
}

// ─── Comparisons (Phase 3B) ─────────────────────────────────────────────────

export function getReportComparisons(
  reportId: string,
  signal?: AbortSignal,
): Promise<ComparisonListResponse> {
  return get<ComparisonListResponse>(
    `/reports/${reportId}/comparisons`,
    signal,
  );
}

export function getCompanyComparisons(
  companyId: string,
  comparisonType?: string,
  signal?: AbortSignal,
): Promise<ComparisonListResponse> {
  const params = comparisonType
    ? `?comparison_type=${encodeURIComponent(comparisonType)}`
    : "";
  return get<ComparisonListResponse>(
    `/companies/${companyId}/comparisons${params}`,
    signal,
  );
}

export function getCompanyComparisonSummary(
  companyId: string,
  signal?: AbortSignal,
): Promise<ComparisonSummaryResponse> {
  return get<ComparisonSummaryResponse>(
    `/companies/${companyId}/comparison-summary`,
    signal,
  );
}

// ─── Analytics (Phase 3C) ───────────────────────────────────────────────────

export function getReportAnalytics(
  reportId: string,
  signal?: AbortSignal,
): Promise<AnalyticsListResponse> {
  return get<AnalyticsListResponse>(
    `/reports/${reportId}/analytics`,
    signal,
  );
}

export function getCompanyAnalytics(
  companyId: string,
  signalType?: string,
  signal?: AbortSignal,
): Promise<AnalyticsListResponse> {
  const params = signalType
    ? `?signal_type=${encodeURIComponent(signalType)}`
    : "";
  return get<AnalyticsListResponse>(
    `/companies/${companyId}/analytics${params}`,
    signal,
  );
}

export function getCompanyAnalyticsSummary(
  companyId: string,
  signal?: AbortSignal,
): Promise<AnalyticsSummaryResponse> {
  return get<AnalyticsSummaryResponse>(
    `/companies/${companyId}/analytics-summary`,
    signal,
  );
}
