import PageHeader from "@/components/PageHeader";
import MetricCard from "@/components/MetricCard";
import SectionPanel from "@/components/SectionPanel";
import Skeleton from "@/design-system/components/Skeleton";
import ErrorFallback from "@/design-system/patterns/ErrorFallback";
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
        <Skeleton variant="chart" />
        <div className="space-y-3">
          <Skeleton variant="text" className="w-full h-12" />
          <Skeleton variant="text" className="w-full h-12" />
          <Skeleton variant="text" className="w-full h-12" />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorFallback
        title="Tone Ingestion Failure"
        message="Unable to extract linguistic indicators from the management discussion text."
        resetErrorBoundary={refetch}
      />
    );
  }

  return (
    <div className="space-y-6 animate-slide-up">
      <PageHeader
        title="Management Tone"
        subtitle="Sentiment, confidence, and hedging analysis"
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

      {toneList.length === 0 ? (
        <div className="p-8">
          <EmptyState
            title="No management discussion metrics"
            description="Process a document to run semantic management tone analysis."
          />
        </div>
      ) : (
        <>
          <div className="card-grid">
            <MetricCard label="Average Positive Sentiment" value={`${(avgPos * 100).toFixed(1)}%`} icon={<ThumbsUp className="w-5 h-5 text-success" />} />
            <MetricCard label="Average Negative Sentiment" value={`${(avgNeg * 100).toFixed(1)}%`} icon={<ThumbsDown className="w-5 h-5 text-danger" />} />
            <MetricCard label="Average Hedging Level" value={`${(avgHedge * 100).toFixed(1)}%`} icon={<AlertTriangle className="w-5 h-5 text-warning" />} />
            <MetricCard label="Linguistic Confidence" value={`${(avgConf * 100).toFixed(1)}%`} icon={<Users className="w-5 h-5 text-brand-600" />} />
          </div>

          <SectionPanel title="Confidence & Hedging Trends">
            <ConfidenceTrendChart labels={labels} confidence={confData} hedging={hedgeData} />
          </SectionPanel>

          <SectionPanel title="Management Discussion Sentiment Breakdown" badge={<span className="badge-neutral">{toneList.length} segments</span>}>
            <div className="space-y-4">
              {toneList.map((t) => (
                <div key={t.id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-lg bg-white border border-surface-200 hover:border-brand-300 transition-colors shadow-sm">
                  <div className="flex items-start gap-3 min-w-0">
                    <div className={clsx("w-2.5 h-2.5 rounded-full shrink-0 mt-1.5", t.sentiment === "POSITIVE" ? "bg-success" : t.sentiment === "NEGATIVE" ? "bg-danger" : "bg-surface-400")} />
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-bold text-surface-900">{t.source_type}</span>
                        <span className={clsx("text-[10px] font-semibold px-2 py-0.5 rounded-full",
                          t.sentiment === "POSITIVE" ? "bg-success-light text-success-dark" :
                          t.sentiment === "NEGATIVE" ? "bg-danger-light text-danger-dark" :
                          "bg-surface-100 text-surface-600"
                        )}>
                          {t.sentiment}
                        </span>
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-surface-100 text-surface-650 font-mono">
                          {t.confidence_level}
                        </span>
                      </div>
                      {t.source_text && (
                        <p className="text-xs text-surface-600 mt-2 italic bg-surface-50 p-2.5 rounded border-l-2 border-surface-300 leading-relaxed">
                          "{t.source_text}"
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-row sm:flex-col items-center sm:items-end justify-between sm:justify-start gap-4 sm:gap-1 border-t sm:border-t-0 pt-3 sm:pt-0 border-surface-100 font-mono text-xs">
                    <div className="flex gap-3">
                      <span className="text-success-dark">Pos: {(t.positive_score * 100).toFixed(0)}%</span>
                      <span className="text-danger-dark">Neg: {(t.negative_score * 100).toFixed(0)}%</span>
                      <span className="text-warning-dark">Hedge: {(t.hedging_score * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </SectionPanel>
        </>
      )}
    </div>
  );
}
