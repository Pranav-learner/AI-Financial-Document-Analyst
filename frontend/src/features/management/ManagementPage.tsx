import PageHeader from "@/components/PageHeader";
import MetricCard from "@/components/MetricCard";
import SectionPanel from "@/components/SectionPanel";
import LoadingPanel from "@/components/LoadingPanel";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import ConfidenceTrendChart from "@/components/charts/ConfidenceTrendChart";
import { useReports } from "@/hooks/useReports";
import { useReportTone } from "@/hooks/useManagement";
import { useState } from "react";
import { Users, ThumbsUp, ThumbsDown, AlertTriangle } from "lucide-react";
import { clsx } from "clsx";

export default function ManagementPage() {
  const { data: reportsData } = useReports(10, 0);
  const reports = reportsData?.items ?? [];
  const [selectedReport, setSelectedReport] = useState("");
  const reportId = selectedReport || reports[0]?.id;
  const { data: tones, isLoading, isError, refetch } = useReportTone(reportId);
  const toneList = tones ?? [];

  const avgPos = toneList.length ? toneList.reduce((s, t) => s + t.positive_score, 0) / toneList.length : 0;
  const avgNeg = toneList.length ? toneList.reduce((s, t) => s + t.negative_score, 0) / toneList.length : 0;
  const avgHedge = toneList.length ? toneList.reduce((s, t) => s + t.hedging_score, 0) / toneList.length : 0;
  const avgConf = toneList.length ? toneList.reduce((s, t) => s + t.confidence_score, 0) / toneList.length : 0;

  const labels = toneList.map((_, i) => `Segment ${i + 1}`);
  const confData = toneList.map((t) => t.confidence_score);
  const hedgeData = toneList.map((t) => t.hedging_score);

  if (isLoading) return <LoadingPanel rows={6} />;
  if (isError) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div className="space-y-6 animate-slide-up">
      <PageHeader title="Management Tone" subtitle="Sentiment, confidence, and hedging analysis" actions={
        <select value={selectedReport} onChange={(e) => setSelectedReport(e.target.value)} className="text-sm border border-surface-200 rounded-lg px-3 py-2 bg-white" aria-label="Select report">
          <option value="">Latest Report</option>
          {reports.map((r) => <option key={r.id} value={r.id}>{r.report_type} {r.year}{r.quarter ? ` Q${r.quarter}` : ""}</option>)}
        </select>
      } />

      {toneList.length === 0 ? <EmptyState title="No tone data" description="Process a document to extract management tone signals." /> : (<>
        <div className="card-grid">
          <MetricCard label="Avg Positive" value={`${(avgPos * 100).toFixed(1)}%`} icon={<ThumbsUp className="w-5 h-5" />} />
          <MetricCard label="Avg Negative" value={`${(avgNeg * 100).toFixed(1)}%`} icon={<ThumbsDown className="w-5 h-5" />} />
          <MetricCard label="Avg Hedging" value={`${(avgHedge * 100).toFixed(1)}%`} icon={<AlertTriangle className="w-5 h-5" />} />
          <MetricCard label="Avg Confidence" value={`${(avgConf * 100).toFixed(1)}%`} icon={<Users className="w-5 h-5" />} />
        </div>

        <SectionPanel title="Confidence & Hedging Trends">
          <ConfidenceTrendChart labels={labels} confidence={confData} hedging={hedgeData} />
        </SectionPanel>

        <SectionPanel title="Sentiment Breakdown" badge={<span className="badge-neutral">{toneList.length} segments</span>}>
          <div className="space-y-3">
            {toneList.map((t) => (
              <div key={t.id} className="flex items-center gap-4 p-3 rounded-lg bg-surface-50">
                <div className={clsx("w-2 h-2 rounded-full shrink-0", t.sentiment === "POSITIVE" ? "bg-success" : t.sentiment === "NEGATIVE" ? "bg-danger" : "bg-surface-400")} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-surface-800">{t.source_type}</span>
                    <span className={clsx("badge", t.sentiment === "POSITIVE" ? "badge-success" : t.sentiment === "NEGATIVE" ? "badge-danger" : "badge-neutral")}>{t.sentiment}</span>
                    <span className="badge-neutral">{t.confidence_level}</span>
                  </div>
                  <div className="flex gap-4 mt-1 text-xs text-surface-500">
                    <span>Positive: {(t.positive_score * 100).toFixed(0)}%</span>
                    <span>Negative: {(t.negative_score * 100).toFixed(0)}%</span>
                    <span>Hedging: {(t.hedging_score * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </SectionPanel>
      </>)}
    </div>
  );
}
