import PageHeader from "@/components/PageHeader";
import MetricCard from "@/components/MetricCard";
import LoadingPanel from "@/components/LoadingPanel";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import { useReports } from "@/hooks/useReports";
import {
  BarChart3,
  ShieldAlert,
  Users,
  FileText,
  Clock,
  Activity,
} from "lucide-react";
import { Link } from "react-router-dom";

/** Executive Dashboard — high-level company intelligence overview. */
export default function DashboardPage() {
  const { data, isLoading, isError, refetch } = useReports(20, 0);

  if (isLoading) return <LoadingPanel rows={6} />;
  if (isError)
    return <ErrorState message="Failed to load dashboard data." onRetry={() => refetch()} />;

  const reports = data?.items ?? [];
  const latestReport = reports[0];
  const processed = reports.filter((r) => ["EMBEDDED", "COMPLETED", "READY"].includes(r.status));
  const failed = reports.filter((r) => r.status === "FAILED");

  return (
    <div className="space-y-6 animate-slide-up">
      <PageHeader
        title="Executive Dashboard"
        subtitle="AI Financial Document Analyst — Intelligence Overview"
      />

      {/* Quick Stats */}
      <div className="card-grid">
        <MetricCard
          label="Total Reports"
          value={data?.total ?? 0}
          icon={<BarChart3 className="w-5 h-5" />}
        />
        <MetricCard
          label="Processed"
          value={processed.length}
          icon={<Activity className="w-5 h-5" />}
        />
        <MetricCard
          label="Failed"
          value={failed.length}
          icon={<ShieldAlert className="w-5 h-5" />}
        />
        <MetricCard
          label="Latest Filing"
          value={latestReport?.report_type ?? "—"}
          icon={<FileText className="w-5 h-5" />}
        />
      </div>

      {/* Quick Navigation */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[
          {
            to: "/financial",
            label: "Financial Analysis",
            desc: "Revenue trends, margins, growth metrics",
            icon: BarChart3,
            color: "bg-brand-50 text-brand-600",
          },
          {
            to: "/risks",
            label: "Risk Intelligence",
            desc: "Risk factors, evolution tracking, severity",
            icon: ShieldAlert,
            color: "bg-danger-light text-danger-dark",
          },
          {
            to: "/management",
            label: "Management Tone",
            desc: "Sentiment, confidence, hedging analysis",
            icon: Users,
            color: "bg-success-light text-success-dark",
          },
        ].map(({ to, label, desc, icon: Icon, color }) => (
          <Link
            key={to}
            to={to}
            className="glass-panel-hover p-5 flex items-start gap-4 group"
          >
            <div
              className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${color}`}
            >
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-surface-800 group-hover:text-brand-700 transition-colors">
                {label}
              </h3>
              <p className="text-xs text-surface-500 mt-0.5">{desc}</p>
            </div>
          </Link>
        ))}
      </div>

      {/* Recent Activity Feed */}
      <div className="glass-panel">
        <div className="px-5 py-4 border-b border-surface-100">
          <h3 className="section-title flex items-center gap-2">
            <Clock className="w-4 h-4 text-surface-400" />
            Recent Activity
          </h3>
        </div>
        <div className="divide-y divide-surface-100">
          {reports.length === 0 ? (
            <EmptyState
              title="No activity yet"
              description="Upload a financial document to get started."
            />
          ) : (
            reports.slice(0, 8).map((r) => (
              <div
                key={r.id}
                className="px-5 py-3 flex items-center justify-between hover:bg-surface-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-2 h-2 rounded-full shrink-0 ${
                      r.status === "FAILED"
                        ? "bg-danger"
                        : ["EMBEDDED", "COMPLETED", "READY"].includes(r.status)
                          ? "bg-success"
                          : "bg-warning"
                    }`}
                  />
                  <div>
                    <span className="text-sm font-medium text-surface-800">
                      {r.original_filename ?? `Report ${r.id.slice(0, 8)}`}
                    </span>
                    <span className="text-xs text-surface-400 ml-2">
                      {r.report_type} · {r.year}
                      {r.quarter ? ` Q${r.quarter}` : ""}
                    </span>
                  </div>
                </div>
                <span className="badge-neutral">{r.status}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
