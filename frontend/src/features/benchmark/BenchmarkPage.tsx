import PageHeader from "@/components/PageHeader";
import SectionPanel from "@/components/SectionPanel";
import DataTable, { type Column } from "@/components/DataTable";
import LoadingPanel from "@/components/LoadingPanel";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import BenchmarkBadge from "@/components/BenchmarkBadge";
import ScoreCard from "@/components/ScoreCard";
import BenchmarkRadarChart from "@/components/charts/BenchmarkRadarChart";
import BenchmarkBarChart from "@/components/charts/BenchmarkBarChart";
import { useBenchmarkRun, useBenchmarkSummary } from "@/hooks/useBenchmark";
import type { BenchmarkSummary } from "@/types/api";
import { useState } from "react";
import { Target } from "lucide-react";

export default function BenchmarkPage() {
  const [runId, setRunId] = useState("");
  const { data: run } = useBenchmarkRun(runId || undefined);
  const { data: summaries, isLoading, isError, refetch } = useBenchmarkSummary(runId || undefined);
  const summaryList = summaries ?? [];

  const columns: Column<BenchmarkSummary>[] = [
    { key: "company_id", header: "Company", render: (s) => s.company_id.slice(0, 8) + "…" },
    { key: "financial_score", header: "Financial", align: "center", sortable: true, render: (s) => s.financial_score?.toFixed(1) ?? "—" },
    { key: "risk_score", header: "Risk", align: "center", sortable: true, render: (s) => s.risk_score?.toFixed(1) ?? "—" },
    { key: "tone_score", header: "Tone", align: "center", sortable: true, render: (s) => s.tone_score?.toFixed(1) ?? "—" },
    { key: "capital_allocation_score", header: "Capital", align: "center", sortable: true, render: (s) => s.capital_allocation_score?.toFixed(1) ?? "—" },
    { key: "overall_score", header: "Overall", align: "center", sortable: true, render: (s) => <span className="font-bold">{s.overall_score?.toFixed(1) ?? "—"}</span> },
    { key: "rank", header: "Rank", align: "center", render: (s) => <BenchmarkBadge rank={s.rank} /> },
  ];

  const radarIndicators = ["Financial", "Risk", "Tone", "Capital Allocation"];
  const radarSeries = summaryList.map((s) => ({
    name: s.company_id.slice(0, 8),
    values: [s.financial_score ?? 0, s.risk_score ?? 0, s.tone_score ?? 0, s.capital_allocation_score ?? 0],
  }));

  const barCompanies = summaryList.map((s) => s.company_id.slice(0, 8));
  const barScores = summaryList.map((s) => s.overall_score ?? 0);

  return (
    <div className="space-y-6 animate-slide-up">
      <PageHeader title="Benchmark Analysis" subtitle="Competitor comparison, rankings, and dimension scores" actions={
        <div className="flex items-center gap-2">
          <input type="text" placeholder="Enter benchmark run ID…" value={runId} onChange={(e) => setRunId(e.target.value)} className="text-sm border border-surface-200 rounded-lg px-3 py-2 bg-white w-64" aria-label="Benchmark run ID" />
        </div>
      } />

      {!runId && <EmptyState title="Enter a benchmark run ID" description="Enter a benchmark run ID above to view results, or create a new benchmark run via the API." icon={<Target className="w-7 h-7 text-surface-400" />} />}

      {runId && isLoading && <LoadingPanel rows={6} />}
      {runId && isError && <ErrorState onRetry={() => refetch()} />}

      {summaryList.length > 0 && (<>
        {run && <div className="glass-panel p-4 text-sm text-surface-600">
          <span className="font-medium text-surface-800">{run.run_name}</span> · Status: <span className="badge-neutral">{run.status}</span> · {run.company_ids.length} companies
        </div>}

        <div className="flex flex-wrap justify-center gap-6">
          {summaryList.sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99)).slice(0, 5).map((s) => (
            <ScoreCard key={s.id} label={`Company ${s.company_id.slice(0, 6)}`} score={s.overall_score} size="lg" />
          ))}
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <SectionPanel title="Dimension Radar"><BenchmarkRadarChart indicators={radarIndicators} series={radarSeries} /></SectionPanel>
          <SectionPanel title="Overall Rankings"><BenchmarkBarChart companies={barCompanies} scores={barScores} label="Overall Score" /></SectionPanel>
        </div>

        <SectionPanel title="Leaderboard" badge={<span className="badge-info">{summaryList.length} companies</span>}>
          <DataTable columns={columns} data={summaryList} keyExtractor={(s) => s.id} />
        </SectionPanel>
      </>)}
    </div>
  );
}
