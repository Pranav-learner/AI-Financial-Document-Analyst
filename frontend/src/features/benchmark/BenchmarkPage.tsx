import PageHeader from "@/components/PageHeader";
import SectionPanel from "@/components/SectionPanel";
import DataTable, { type Column } from "@/components/DataTable";
import Skeleton from "@/design-system/components/Skeleton";
import ErrorFallback from "@/design-system/patterns/ErrorFallback";
import EmptyState from "@/components/EmptyState";
import BenchmarkBadge from "@/components/BenchmarkBadge";
import BenchmarkRadarChart from "@/components/charts/BenchmarkRadarChart";
import BenchmarkBarChart from "@/components/charts/BenchmarkBarChart";
import { useBenchmarkRun, useBenchmarkSummary } from "@/hooks/useBenchmark";
import type { BenchmarkSummary } from "@/types/api";
import { useState } from "react";
import { Target, Trophy, Award, Medal } from "lucide-react";
import { clsx } from "clsx";

export default function BenchmarkPage() {
  const [runId, setRunId] = useState("");
  const { data: run } = useBenchmarkRun(runId || undefined);
  const { data: summaries, isLoading, isError, refetch } = useBenchmarkSummary(runId || undefined);
  const summaryList = summaries ?? [];

  const columns: Column<BenchmarkSummary>[] = [
    { key: "company_id", header: "Company ID", render: (s) => <span className="font-mono text-xs">{s.company_id}</span> },
    { key: "financial_score", header: "Financial Score", align: "center", sortable: true, render: (s) => s.financial_score?.toFixed(1) ?? "—" },
    { key: "risk_score", header: "Risk Mitigation", align: "center", sortable: true, render: (s) => s.risk_score?.toFixed(1) ?? "—" },
    { key: "tone_score", header: "Sentiment Score", align: "center", sortable: true, render: (s) => s.tone_score?.toFixed(1) ?? "—" },
    { key: "capital_allocation_score", header: "Capital Allocation", align: "center", sortable: true, render: (s) => s.capital_allocation_score?.toFixed(1) ?? "—" },
    { key: "overall_score", header: "Overall Rating", align: "center", sortable: true, render: (s) => <span className="font-bold text-brand-700">{s.overall_score?.toFixed(1) ?? "—"}</span> },
    { key: "rank", header: "Current Rank", align: "center", render: (s) => <BenchmarkBadge rank={s.rank} /> },
  ];

  const radarIndicators = ["Financial", "Risk", "Tone", "Capital Allocation"];
  const radarSeries = summaryList.map((s) => ({
    name: s.company_id.slice(0, 8),
    values: [s.financial_score ?? 0, s.risk_score ?? 0, s.tone_score ?? 0, s.capital_allocation_score ?? 0],
  }));

  const barCompanies = summaryList.map((s) => s.company_id.slice(0, 8));
  const barScores = summaryList.map((s) => s.overall_score ?? 0);

  // Sorting for the podium presentation
  const sortedPodium = [...summaryList].sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99)).slice(0, 3);
  
  // Arrange top 3 as: 2nd place, 1st place, 3rd place for visual podium
  const arrangedPodium = [];
  if (sortedPodium[1]) arrangedPodium.push({ ...sortedPodium[1], place: 2 });
  if (sortedPodium[0]) arrangedPodium.push({ ...sortedPodium[0], place: 1 });
  if (sortedPodium[2]) arrangedPodium.push({ ...sortedPodium[2], place: 3 });

  if (runId && isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton variant="text" className="w-1/3 h-8" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
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

  if (runId && isError) {
    return (
      <ErrorFallback
        title="Benchmarking Engine Failure"
        message="Failed to retrieve cross-company normalization scores."
        resetErrorBoundary={refetch}
      />
    );
  }

  return (
    <div className="space-y-6 animate-slide-up">
      <PageHeader
        title="Benchmark Analysis"
        subtitle="Competitor comparison, rankings, and dimension scores"
        actions={
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Enter benchmark run ID (e.g. run-01)…"
              value={runId}
              onChange={(e) => setRunId(e.target.value)}
              className="text-sm border border-surface-200 rounded-lg px-3 py-2 bg-white w-64 focus:ring-2 focus:ring-brand-500 focus:outline-none"
              aria-label="Benchmark run ID"
            />
          </div>
        }
      />

      {!runId && (
        <div className="p-8">
          <EmptyState
            title="Enter a benchmark run ID"
            description="Provide a benchmark run ID above (e.g., 'run-01') to load the comparative evaluation model."
            icon={<Target className="w-7 h-7 text-brand-650" />}
          />
        </div>
      )}

      {summaryList.length > 0 && (
        <>
          {run && (
            <div className="glass-panel p-4 text-sm text-surface-700 bg-brand-50/20 border-brand-200/50 flex items-center justify-between">
              <div>
                <span className="font-bold text-surface-900">{run.run_name}</span> · Status:{" "}
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-success-light text-success-dark">
                  {run.status}
                </span>
              </div>
              <span className="text-xs text-surface-450 font-mono">
                {run.company_ids.length} companies benchmarked
              </span>
            </div>
          )}

          {/* Visual Podium for top 3 companies */}
          {sortedPodium.length > 0 && (
            <div className="glass-panel p-6">
              <h3 className="section-title flex items-center gap-2 mb-6 justify-center">
                <Trophy className="w-5 h-5 text-warning" />
                Benchmark Leaderboard Podium
              </h3>
              
              <div className="flex flex-col sm:flex-row items-end justify-center gap-6 pt-8 pb-4">
                {arrangedPodium.map((comp) => {
                  const isFirst = comp.place === 1;
                  const isSecond = comp.place === 2;
                  
                  return (
                    <div
                      key={comp.id}
                      className={clsx(
                        "flex flex-col items-center justify-end w-full sm:w-48 transition-all hover:scale-[1.02] duration-200",
                        isFirst ? "order-2 sm:-translate-y-4" : isSecond ? "order-1" : "order-3"
                      )}
                    >
                      {/* Avatar/Trophy Icon */}
                      <div className="mb-3 relative">
                        {isFirst && (
                          <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-warning animate-bounce">
                            <Trophy className="w-6 h-6 fill-warning/20" />
                          </div>
                        )}
                        <div
                          className={clsx(
                            "w-12 h-12 rounded-full flex items-center justify-center border-2 shadow-md",
                            isFirst
                              ? "bg-warning-light border-warning text-warning-dark"
                              : isSecond
                                ? "bg-slate-100 border-slate-400 text-slate-700"
                                : "bg-orange-50 border-orange-350 text-orange-700"
                          )}
                        >
                          {isFirst ? (
                            <Award className="w-6 h-6" />
                          ) : (
                            <Medal className="w-6 h-6" />
                          )}
                        </div>
                      </div>

                      {/* Bar Podium */}
                      <div
                        className={clsx(
                          "w-full rounded-t-lg p-4 text-center border-t border-x shadow-sm flex flex-col justify-between items-center",
                          isFirst
                            ? "h-40 bg-gradient-to-b from-warning-light/40 to-warning-light/10 border-warning"
                            : isSecond
                              ? "h-32 bg-gradient-to-b from-slate-100/60 to-slate-50/20 border-slate-300"
                              : "h-24 bg-gradient-to-b from-orange-50/40 to-orange-50/10 border-orange-200"
                        )}
                      >
                        <div>
                          <span className="text-[10px] font-bold text-surface-450 uppercase block">
                            Rank {comp.place}
                          </span>
                          <span className="text-xs font-semibold text-surface-800 block truncate max-w-[140px] mt-1 font-mono">
                            {comp.company_id}
                          </span>
                        </div>
                        <div className="mt-2">
                          <span className="text-2xl font-bold text-surface-900">
                            {comp.overall_score?.toFixed(1)}
                          </span>
                          <span className="text-[10px] text-surface-450 block">Overall Rating</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className="grid gap-6 lg:grid-cols-2">
            <SectionPanel title="Performance Dimension Overlays">
              <BenchmarkRadarChart indicators={radarIndicators} series={radarSeries} />
            </SectionPanel>
            <SectionPanel title="Overall Rating Benchmarks">
              <BenchmarkBarChart companies={barCompanies} scores={barScores} label="Overall Score" />
            </SectionPanel>
          </div>

          <SectionPanel title="Leaderboard Registry" badge={<span className="badge-neutral">{summaryList.length} companies</span>}>
            <DataTable columns={columns} data={summaryList} keyExtractor={(s) => s.id} />
          </SectionPanel>
        </>
      )}
    </div>
  );
}
