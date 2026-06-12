/**
 * Management tone service — tone records, evolution, company summaries.
 */

import { get } from "./api";
import type {
  ManagementTone,
  ToneEvolution,
  CompanyToneSummary,
} from "@/types/api";

export function getReportTone(
  reportId: string,
  signal?: AbortSignal,
): Promise<ManagementTone[]> {
  return get<ManagementTone[]>(`/reports/${reportId}/tone`, signal);
}

export function getReportToneDetail(
  reportId: string,
  toneId: string,
  signal?: AbortSignal,
): Promise<ManagementTone> {
  return get<ManagementTone>(
    `/reports/${reportId}/tone/${toneId}`,
    signal,
  );
}

export function getCompanyTone(
  companyId: string,
  signal?: AbortSignal,
): Promise<ManagementTone[]> {
  return get<ManagementTone[]>(`/companies/${companyId}/tone`, signal);
}

export function getToneEvolution(
  companyId: string,
  signal?: AbortSignal,
): Promise<ToneEvolution[]> {
  return get<ToneEvolution[]>(
    `/companies/${companyId}/tone-evolution`,
    signal,
  );
}

export function getToneSummary(
  companyId: string,
  signal?: AbortSignal,
): Promise<CompanyToneSummary> {
  return get<CompanyToneSummary>(
    `/companies/${companyId}/tone-summary`,
    signal,
  );
}
