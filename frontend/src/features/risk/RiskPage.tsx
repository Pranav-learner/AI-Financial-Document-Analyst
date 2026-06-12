import PageHeader from "@/components/PageHeader";
import MetricCard from "@/components/MetricCard";
import SectionPanel from "@/components/SectionPanel";
import DataTable, { type Column } from "@/components/DataTable";
import LoadingPanel from "@/components/LoadingPanel";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import RiskBadge from "@/components/RiskBadge";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import RiskDistributionChart from "@/components/charts/RiskDistributionChart";
import { useReports } from "@/hooks/useReports";
import { useReportRisks } from "@/hooks/useRisks";
import type { RiskFactor } from "@/types/api";
import { ShieldAlert, AlertTriangle, CheckCircle, TrendingUp } from "lucide-react";
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
  risks.forEach((r) => { byCategory[r.category] = (byCategory[r.category] ?? 0) + 1; bySeverity[r.severity] = (bySeverity[r.severity] ?? 0) + 1; });
  const categoryData = Object.entries(byCategory).map(([name, value]) => ({ name, value }));
  const severityData = Object.entries(bySeverity).map(([name, value]) => ({ name, value }));
  const high = risks.filter((r) => ["HIGH","CRITICAL"].includes(r.severity)).length;
  const medium = risks.filter((r) => ["MEDIUM","MODERATE"].includes(r.severity)).length;
  const low = risks.filter((r) => ["LOW","MINIMAL"].includes(r.severity)).length;
  const [selected, setSelected] = useState<RiskFactor | null>(null);

  const columns: Column<RiskFactor>[] = [
    { key: "risk_name", header: "Risk", sortable: true, render: (r) => <button type="button" onClick={() => setSelected(r)} className="text-left text-sm font-medium text-brand-700 hover:underline">{r.risk_name}</button> },
    { key: "category", header: "Category", sortable: true },
    { key: "severity", header: "Severity", sortable: true, render: (r) => <RiskBadge severity={r.severity} /> },
    { key: "confidence_score", header: "Confidence", align: "center", render: (r) => <ConfidenceBadge score={r.confidence_score} /> },
  ];

  if (isLoading) return <LoadingPanel rows={6} />;
  if (isError) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div className="space-y-6 animate-slide-up">
      <PageHeader title="Risk Intelligence" subtitle="Risk factors, severity distribution, evolution tracking" actions={
        <select value={selectedReport} onChange={(e) => setSelectedReport(e.target.value)} className="text-sm border border-surface-200 rounded-lg px-3 py-2 bg-white" aria-label="Select report">
          <option value="">Latest Report</option>
          {reports.map((r) => <option key={r.id} value={r.id}>{r.report_type} {r.year}{r.quarter ? ` Q${r.quarter}` : ""}</option>)}
        </select>
      } />
      {risks.length === 0 ? <EmptyState title="No risk data" description="Process a document to extract risk factors." /> : (<>
        <div className="card-grid">
          <MetricCard label="Total Risks" value={risks.length} icon={<ShieldAlert className="w-5 h-5" />} />
          <MetricCard label="High/Critical" value={high} icon={<AlertTriangle className="w-5 h-5" />} />
          <MetricCard label="Medium" value={medium} icon={<TrendingUp className="w-5 h-5" />} />
          <MetricCard label="Low" value={low} icon={<CheckCircle className="w-5 h-5" />} />
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {categoryData.length > 0 && <SectionPanel title="By Category"><RiskDistributionChart data={categoryData} title="Category" /></SectionPanel>}
          {severityData.length > 0 && <SectionPanel title="By Severity"><RiskDistributionChart data={severityData} title="Severity" /></SectionPanel>}
        </div>
        <SectionPanel title="All Risk Factors" badge={<span className="badge-danger">{risks.length}</span>}>
          <DataTable columns={columns} data={risks} keyExtractor={(r) => r.id} />
        </SectionPanel>
        {selected && (
          <div className="fixed inset-y-0 right-0 w-full max-w-lg bg-white shadow-2xl border-l border-surface-200 z-50 animate-slide-in-right overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-bold">Risk Detail</h2>
                <button onClick={() => setSelected(null)} className="text-surface-400 hover:text-surface-700 text-xl" type="button" aria-label="Close">×</button>
              </div>
              <div className="space-y-4">
                <div><span className="metric-label">Risk Name</span><p className="text-sm font-semibold mt-1">{selected.risk_name}</p></div>
                <div className="flex gap-4">
                  <div><span className="metric-label">Category</span><p className="mt-1 text-sm">{selected.category}</p></div>
                  <div><span className="metric-label">Severity</span><div className="mt-1"><RiskBadge severity={selected.severity} /></div></div>
                  <div><span className="metric-label">Confidence</span><div className="mt-1"><ConfidenceBadge score={selected.confidence_score} /></div></div>
                </div>
                <div><span className="metric-label">Description</span><p className="text-sm text-surface-600 mt-1 leading-relaxed">{selected.risk_description}</p></div>
                {selected.source_text && <div><span className="metric-label">Source</span><p className="text-xs text-surface-500 mt-1 p-3 bg-surface-50 rounded-lg italic">"{selected.source_text}"</p></div>}
              </div>
            </div>
          </div>
        )}
      </>)}
    </div>
  );
}
