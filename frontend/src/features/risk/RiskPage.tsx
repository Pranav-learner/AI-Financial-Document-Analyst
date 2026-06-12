import PageHeader from "@/components/PageHeader";
import MetricCard from "@/components/MetricCard";
import SectionPanel from "@/components/SectionPanel";
import DataTable, { type Column } from "@/components/DataTable";
import Skeleton from "@/design-system/components/Skeleton";
import ErrorFallback from "@/design-system/patterns/ErrorFallback";
import EmptyState from "@/components/EmptyState";
import RiskBadge from "@/components/RiskBadge";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import RiskDistributionChart from "@/components/charts/RiskDistributionChart";
import { useReports } from "@/hooks/useReports";
import { useReportRisks } from "@/hooks/useRisks";
import type { RiskFactor } from "@/types/api";
import { ShieldAlert, AlertTriangle, CheckCircle, TrendingUp, X } from "lucide-react";
import { useState } from "react";

export default function RiskPage() {
  const { data: reportsData } = useReports(10, 0);
  const reports = reportsData?.items ?? [];
  const [selectedReport, setSelectedReport] = useState("");
  const reportId = selectedReport || reports[0]?.id;
  const { data: risksData, isLoading, isError, refetch } = useReportRisks(reportId);
  const risks = risksData?.items ?? [];
  const byCategory: Record<string, number> = {};
  const bySeverity: Record<string, number> = {};
  risks.forEach((r) => {
    byCategory[r.category] = (byCategory[r.category] ?? 0) + 1;
    bySeverity[r.severity] = (bySeverity[r.severity] ?? 0) + 1;
  });
  const categoryData = Object.entries(byCategory).map(([name, value]) => ({ name, value }));
  const severityData = Object.entries(bySeverity).map(([name, value]) => ({ name, value }));
  const high = risks.filter((r) => ["HIGH","CRITICAL"].includes(r.severity)).length;
  const medium = risks.filter((r) => ["MEDIUM","MODERATE"].includes(r.severity)).length;
  const low = risks.filter((r) => ["LOW","MINIMAL"].includes(r.severity)).length;
  const [selected, setSelected] = useState<RiskFactor | null>(null);

  const columns: Column<RiskFactor>[] = [
    {
      key: "risk_name",
      header: "Risk Factor",
      sortable: true,
      render: (r) => (
        <button
          type="button"
          onClick={() => setSelected(r)}
          className="text-left text-sm font-semibold text-brand-600 hover:text-brand-800 hover:underline transition-colors"
        >
          {r.risk_name}
        </button>
      ),
    },
    { key: "category", header: "Risk Category", sortable: true },
    { key: "severity", header: "Severity Level", sortable: true, render: (r) => <RiskBadge severity={r.severity} /> },
    { key: "confidence_score", header: "Confidence score", align: "center", render: (r) => <ConfidenceBadge score={r.confidence_score} /> },
  ];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton variant="text" className="w-1/3 h-8" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Skeleton variant="card" />
          <Skeleton variant="card" />
          <Skeleton variant="card" />
          <Skeleton variant="card" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Skeleton variant="chart" />
          <Skeleton variant="chart" />
        </div>
        <Skeleton variant="table" />
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorFallback
        title="Risk Engine Timeout"
        message="Could not resolve risk factors from the intelligence engine database."
        resetErrorBoundary={refetch}
      />
    );
  }

  return (
    <div className="space-y-6 animate-slide-up">
      <PageHeader
        title="Risk Intelligence"
        subtitle="Risk factors, severity distribution, evolution tracking"
        actions={
          <select
            value={selectedReport}
            onChange={(e) => setSelectedReport(e.target.value)}
            className="text-sm border border-surface-200 rounded-lg px-3 py-2 bg-white text-surface-700 focus:ring-2 focus:ring-brand-500 focus:outline-none"
            aria-label="Select report"
          >
            <option value="">Latest Report</option>
            {reports.map((r) => (
              <option key={r.id} value={r.id}>
                {r.report_type} {r.year}
                {r.quarter ? ` Q${r.quarter}` : ""} — {r.original_filename?.slice(0, 30)}
              </option>
            ))}
          </select>
        }
      />
      
      {risks.length === 0 ? (
        <div className="p-8">
          <EmptyState title="No risk factors identified" description="This document does not contain any classified risk factors." />
        </div>
      ) : (
        <>
          <div className="card-grid">
            <MetricCard label="Total Identified Risks" value={risks.length} icon={<ShieldAlert className="w-5 h-5 text-brand-600" />} />
            <MetricCard label="High & Critical Risks" value={high} icon={<AlertTriangle className="w-5 h-5 text-danger" />} />
            <MetricCard label="Medium Risks" value={medium} icon={<TrendingUp className="w-5 h-5 text-warning" />} />
            <MetricCard label="Low Risks" value={low} icon={<CheckCircle className="w-5 h-5 text-success" />} />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            {categoryData.length > 0 && (
              <SectionPanel title="Risks by Category">
                <RiskDistributionChart data={categoryData} title="Category" />
              </SectionPanel>
            )}
            {severityData.length > 0 && (
              <SectionPanel title="Risks by Severity">
                <RiskDistributionChart data={severityData} title="Severity" />
              </SectionPanel>
            )}
          </div>

          <SectionPanel title="Risk Factors Registry" badge={<span className="badge-neutral">{risks.length}</span>}>
            <DataTable columns={columns} data={risks} keyExtractor={(r) => r.id} />
          </SectionPanel>

          {/* Premium side drawer with backdrop */}
          {selected && (
            <>
              {/* Overlay Backdrop */}
              <div
                className="fixed inset-0 bg-surface-900/40 backdrop-blur-sm z-40 transition-opacity"
                onClick={() => setSelected(null)}
              />

              <div className="fixed inset-y-0 right-0 w-full max-w-xl bg-white shadow-2xl border-l border-surface-200 z-50 animate-slide-in-right overflow-y-auto flex flex-col">
                <div className="p-6 border-b border-surface-150 flex items-center justify-between bg-surface-50/50">
                  <div>
                    <span className="text-[10px] font-bold text-brand-600 uppercase tracking-wider">
                      Risk Intelligence Detail
                    </span>
                    <h2 className="text-base font-bold text-surface-900 mt-0.5">
                      {selected.risk_name}
                    </h2>
                  </div>
                  <button
                    onClick={() => setSelected(null)}
                    className="p-1.5 rounded-lg text-surface-400 hover:text-surface-600 hover:bg-surface-100 transition-colors"
                    type="button"
                    aria-label="Close details panel"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <div className="p-6 space-y-6 flex-1">
                  <div className="grid grid-cols-3 gap-4 p-4 rounded-lg bg-surface-50 border border-surface-200">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-surface-450 block">
                        Category
                      </span>
                      <p className="mt-1 text-sm font-semibold text-surface-900">
                        {selected.category}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-surface-450 block">
                        Severity
                      </span>
                      <div className="mt-1">
                        <RiskBadge severity={selected.severity} />
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-surface-450 block">
                        Confidence
                      </span>
                      <div className="mt-1">
                        <ConfidenceBadge score={selected.confidence_score} />
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-surface-450 block">
                      Description & Context
                    </span>
                    <p className="text-sm text-surface-700 leading-relaxed bg-white border border-surface-150 rounded-lg p-4 shadow-sm">
                      {selected.risk_description}
                    </p>
                  </div>

                  {selected.source_text && (
                    <div className="space-y-2">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-surface-450 block">
                        Document Source Segment
                      </span>
                      <div className="p-4 bg-surface-50 border-l-4 border-brand-500 rounded-r-lg font-mono text-xs text-surface-700 leading-relaxed italic">
                        "{selected.source_text}"
                      </div>
                    </div>
                  )}
                </div>

                <div className="p-4 border-t border-surface-150 bg-surface-50/50 flex justify-end">
                  <button
                    type="button"
                    onClick={() => setSelected(null)}
                    className="px-4 py-2 text-xs font-semibold border border-surface-250 rounded-lg hover:bg-surface-100 text-surface-650 transition-colors"
                  >
                    Close Panel
                  </button>
                </div>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
