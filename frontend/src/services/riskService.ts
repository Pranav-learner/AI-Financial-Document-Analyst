/**
 * Risk intelligence service — risk factors, evolution, summaries.
 */

import { get } from "./api";
import type {
  RiskListResponse,
  RiskEvolutionListResponse,
  RiskSummaryResponse,
  RiskFactor,
} from "@/types/api";

export function getReportRisks(
  reportId: string,
  category?: string,
  signal?: AbortSignal,
): Promise<RiskListResponse> {
  const params = category ? `?category=${encodeURIComponent(category)}` : "";
  return get<RiskListResponse>(
    `/reports/${reportId}/risks${params}`,
    signal,
  );
}

export function getReportRisk(
  reportId: string,
  riskId: string,
  signal?: AbortSignal,
): Promise<RiskFactor> {
  return get<RiskFactor>(
    `/reports/${reportId}/risks/${riskId}`,
    signal,
  );
}

export function getCompanyRisks(
  companyId: string,
  category?: string,
  severity?: string,
  signal?: AbortSignal,
): Promise<RiskListResponse> {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (severity) params.set("severity", severity);
  const qs = params.toString() ? `?${params.toString()}` : "";
  return get<RiskListResponse>(
    `/companies/${companyId}/risks${qs}`,
    signal,
  );
}

export function getRiskEvolution(
  companyId: string,
  evolutionType?: string,
  signal?: AbortSignal,
): Promise<RiskEvolutionListResponse> {
  const params = evolutionType
    ? `?evolution_type=${encodeURIComponent(evolutionType)}`
    : "";
  return get<RiskEvolutionListResponse>(
    `/companies/${companyId}/risk-evolution${params}`,
    signal,
  );
}

export function getRiskSummary(
  companyId: string,
  signal?: AbortSignal,
): Promise<RiskSummaryResponse> {
  return get<RiskSummaryResponse>(
    `/companies/${companyId}/risk-summary`,
    signal,
  );
}
