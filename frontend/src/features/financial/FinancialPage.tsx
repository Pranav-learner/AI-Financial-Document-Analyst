import { useState } from "react";
import PageHeader from "@/components/PageHeader";
import MetricCard from "@/components/MetricCard";
import SectionPanel from "@/components/SectionPanel";
import DataTable, { type Column } from "@/components/DataTable";
import Skeleton from "@/design-system/components/Skeleton";
import ErrorFallback from "@/design-system/patterns/ErrorFallback";
import EmptyState from "@/components/EmptyState";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import RevenueTrendChart from "@/components/charts/RevenueTrendChart";
import MarginTrendChart from "@/components/charts/MarginTrendChart";
import { useReports } from "@/hooks/useReports";
import { useMetrics, useReportComparisons, useReportAnalytics } from "@/hooks/useFinancials";
import type { FinancialMetric, MetricComparison } from "@/types/api";
import { DollarSign, TrendingUp, Percent, TrendingDown, Minus } from "lucide-react";

/** Financial Analysis Workspace — metrics, trends, comparisons. */
export default function FinancialPage() {
  const { data: reportsData } = useReports(10, 0);
  const reports = reportsData?.items ?? [];
  const [selectedReport, setSelectedReport] = useState<string>("");
  const reportId = selectedReport || reports[0]?.id;

  const { data: metricsData, isLoading: metricsLoading, isError: metricsError, refetch: refetchMetrics } = useMetrics(reportId);
  const { data: comparisonsData } = useReportComparisons(reportId);
  const { data: analyticsData } = useReportAnalytics(reportId);

  const metrics = metricsData?.items ?? [];
  const comparisons = comparisonsData?.items ?? [];
  const analytics = analyticsData?.items ?? [];

  // Derive key metrics
  const revenue = metrics.find((m) => {
    const name = m.normalized_metric_name.toUpperCase();
    return name === "REVENUE" || name === "TOTAL_REVENUE";
  });
  const grossMargin = metrics.find((m) => m.normalized_metric_name.toUpperCase() === "GROSS_MARGIN");
  const netIncome = metrics.find((m) => m.normalized_metric_name.toUpperCase() === "NET_INCOME");
  const ebitda = metrics.find((m) => m.normalized_metric_name.toUpperCase() === "EBITDA");

  // Build chart data from comparisons
  const revenueComps = comparisons.filter((c) => c.metric_name.toLowerCase().includes("revenue"));
  const revLabels = revenueComps.map((c) => c.current_period);
  const revValues = revenueComps.map((c) => c.current_value);

  const metricColumns: Column<FinancialMetric>[] = [
    { key: "metric_name", header: "Metric Name", sortable: true },
    { key: "value", header: "Report Value", sortable: true, align: "right", render: (m) => m.value.toLocaleString() },
    { key: "unit", header: "Reporting Unit", render: (m) => m.unit ?? m.currency ?? "—" },
    { key: "metric_category", header: "Metric Category", sortable: true },
    { key: "confidence_score", header: "Confidence score", align: "center", render: (m) => <ConfidenceBadge score={m.confidence_score} /> },
    { key: "extraction_method", header: "Extraction pipeline" },
  ];

  const compColumns: Column<MetricComparison>[] = [
    { key: "metric_name", header: "Metric Name", sortable: true },
    { key: "comparison_type", header: "Comparison Type" },
    { key: "current_value", header: "Current Period", align: "right", render: (c) => c.current_value.toLocaleString() },
    { key: "previous_value", header: "Previous Period", align: "right", render: (c) => c.previous_value.toLocaleString() },
    {
      key: "percentage_change",
      header: "Percentage change",
      align: "right",
      sortable: true,
      render: (c) => {
        if (c.percentage_change == null) return "—";
        const val = c.percentage_change;
        const isPositive = val > 0;
        const isNegative = val < 0;
        
        return (
          <div className="flex items-center justify-end gap-1.5 font-medium">
            {isPositive && <TrendingUp className="w-3.5 h-3.5 text-success" />}
            {isNegative && <TrendingDown className="w-3.5 h-3.5 text-danger" />}
            {!isPositive && !isNegative && <Minus className="w-3.5 h-3.5 text-surface-400" />}
            <span className={isPositive ? "text-success-dark" : isNegative ? "text-danger-dark" : "text-surface-500"}>
              {isPositive ? "+" : ""}{val.toFixed(1)}%
            </span>
          </div>
        );
      },
    },
  ];

  if (metricsLoading) {
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

  if (metricsError) {
    return (
      <ErrorFallback
        title="Financial Pipeline Error"
        message="Unable to fetch extracted financial metrics for this filing."
        resetErrorBoundary={refetchMetrics}
      />
    );
  }

  return (
    <div className="space-y-6 animate-slide-up">
      <PageHeader
        title="Financial Analysis"
        subtitle="Extracted metrics, period comparisons, and financial signals"
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
                {r.report_type} {r.year}{r.quarter ? ` Q${r.quarter}` : ""} — {r.original_filename?.slice(0, 30)}
              </option>
            ))}
          </select>
        }
      />

      {metrics.length === 0 ? (
        <div className="p-8">
          <EmptyState
            title="No financial metrics"
            description="Upload and process a financial document to extract metrics."
          />
        </div>
      ) : (
        <>
          <div className="card-grid">
            <MetricCard
              label="Revenue"
              value={revenue ? `$${revenue.value.toLocaleString()}${revenue.unit === 'BILLION' ? 'B' : 'M'}` : "—"}
              icon={<DollarSign className="w-5 h-5 text-brand-600" />}
            />
            <MetricCard
              label="Gross Margin"
              value={grossMargin ? `${grossMargin.value}%` : "—"}
              icon={<Percent className="w-5 h-5 text-success" />}
            />
            <MetricCard
              label="Net Income"
              value={netIncome ? `$${netIncome.value.toLocaleString()}${netIncome.unit === 'BILLION' ? 'B' : 'M'}` : "—"}
              icon={<TrendingUp className="w-5 h-5 text-indigo-600" />}
            />
            <MetricCard
              label="EBITDA"
              value={ebitda ? `$${ebitda.value.toLocaleString()}${ebitda.unit === 'BILLION' ? 'B' : 'M'}` : "—"}
              icon={<DollarSign className="w-5 h-5 text-warning" />}
            />
          </div>

          {/* Charts */}
          {revValues.length > 0 && (
            <div className="grid gap-4 lg:grid-cols-2">
              <SectionPanel title="Revenue Trend">
                <RevenueTrendChart labels={revLabels} values={revValues} />
              </SectionPanel>
              <SectionPanel title="Margin Trends">
                <MarginTrendChart
                  labels={revLabels}
                  series={[
                    { name: "Gross Margin", data: comparisons.filter((c) => c.metric_name.toLowerCase().includes("gross_margin")).map((c) => c.current_value) },
                    { name: "Operating Margin", data: comparisons.filter((c) => c.metric_name.toLowerCase().includes("operating_margin")).map((c) => c.current_value) },
                  ]}
                />
              </SectionPanel>
            </div>
          )}

          {/* Metrics Table */}
          <SectionPanel title="All Extracted Metrics" badge={<span className="badge-neutral">{metrics.length}</span>}>
            <DataTable columns={metricColumns} data={metrics} keyExtractor={(m) => m.id} />
          </SectionPanel>

          {/* Comparisons Table */}
          {comparisons.length > 0 && (
            <SectionPanel title="Period Comparisons (YoY / QoQ)" badge={<span className="badge-neutral">{comparisons.length}</span>}>
              <DataTable columns={compColumns} data={comparisons} keyExtractor={(c) => c.id} />
            </SectionPanel>
          )}

          {/* Financial Signals */}
          {analytics.length > 0 && (
            <SectionPanel title="Financial Signals" badge={<span className="badge-neutral">{analytics.length}</span>}>
              <div className="grid gap-3 sm:grid-cols-2">
                {analytics.map((a) => (
                  <div key={a.id} className="flex items-start gap-3 p-4 rounded-lg bg-surface-50/50 border border-surface-200">
                    <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${a.severity === "HIGH" ? "bg-danger animate-pulse" : a.severity === "MEDIUM" ? "bg-warning" : "bg-success"}`} />
                    <div>
                      <span className="text-sm font-semibold text-surface-900">{a.signal_code}</span>
                      <p className="text-xs text-surface-650 mt-1 leading-relaxed">{a.explanation ?? `${a.metric_name}: ${a.classification}`}</p>
                    </div>
                  </div>
                ))}
              </div>
            </SectionPanel>
          )}
        </>
      )}
    </div>
  );
}
