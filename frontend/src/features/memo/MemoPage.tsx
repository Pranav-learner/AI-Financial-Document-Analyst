import { useState } from "react";
import PageHeader from "@/components/PageHeader";
import SectionPanel from "@/components/SectionPanel";
import LoadingPanel from "@/components/LoadingPanel";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import CitationBadge from "@/components/CitationBadge";
import { useReports } from "@/hooks/useReports";
import { useMemoDetails, useGenerateMemo, useMemoExport } from "@/hooks/useMemos";
import { FileText, FileDown, Plus } from "lucide-react";

export default function MemoPage() {
  const { data: reportsData } = useReports(10, 0);
  const reports = reportsData?.items ?? [];

  const [selectedReportId, setSelectedReportId] = useState("");
  const [memoId, setMemoId] = useState("");
  const [exportFormat, setExportFormat] = useState<"markdown" | "json" | null>(null);

  const reportId = selectedReportId || (reports.length > 0 ? reports[0].id : "");

  const { data: memo, isLoading, isError, refetch } = useMemoDetails(memoId || undefined);
  const generateMutation = useGenerateMutation();
  const exportQuery = useMemoExport(memoId || undefined, exportFormat || "markdown", !!exportFormat);

  function useGenerateMutation() {
    return useGenerateMemo();
  }

  const handleGenerate = async () => {
    if (!reportId) return;
    const activeReport = reports.find((r) => r.id === reportId);
    if (!activeReport || !activeReport.company_id) {
      alert("Selected report does not have a associated company ID.");
      return;
    }

    try {
      const res = await generateMutation.mutateAsync({
        company_id: activeReport.company_id,
        report_id: reportId,
        memo_type: "single_company",
        title: `Investment Memo: ${activeReport.original_filename || "Company Analysis"}`,
      });
      setMemoId(res.memo_id);
    } catch (err) {
      console.error(err);
    }
  };

  const handleExport = (format: "markdown" | "json") => {
    setExportFormat(format);
  };

  return (
    <div className="space-y-6 animate-slide-up">
      <PageHeader
        title="Investment Memos"
        subtitle="Generate and review LLM-powered investment analysis with citations"
        actions={
          <div className="flex items-center gap-2">
            <select
              value={selectedReportId}
              onChange={(e) => setSelectedReportId(e.target.value)}
              className="text-sm border border-surface-200 rounded-lg px-3 py-2 bg-white"
              aria-label="Select report"
            >
              <option value="">Select a report…</option>
              {reports.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.report_type} {r.year} {r.quarter ? `Q${r.quarter}` : ""} —{" "}
                  {r.original_filename?.slice(0, 30)}
                </option>
              ))}
            </select>

            <button
              onClick={handleGenerate}
              disabled={!reportId || generateMutation.isPending}
              className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors"
              type="button"
            >
              <Plus className="w-4 h-4" />
              {generateMutation.isPending ? "Generating…" : "Generate Memo"}
            </button>
          </div>
        }
      />

      {/* Enter Memo ID Manually if exists */}
      <div className="glass-panel p-4 flex gap-4 items-center">
        <span className="text-sm text-surface-600 font-medium whitespace-nowrap">Load Existing Memo:</span>
        <input
          type="text"
          placeholder="Enter Memo ID…"
          value={memoId}
          onChange={(e) => setMemoId(e.target.value)}
          className="text-sm border border-surface-200 rounded-lg px-3 py-1.5 bg-white w-full max-w-md"
        />
      </div>

      {isLoading && <LoadingPanel rows={6} />}
      {isError && <ErrorState message="Failed to load memo details." onRetry={() => refetch()} />}

      {!isLoading && !isError && !memo && (
        <EmptyState
          title="No investment memo selected"
          description="Select a report and click 'Generate Memo' or enter an existing Memo ID above."
          icon={<FileText className="w-7 h-7 text-surface-400" />}
        />
      )}

      {memo && (
        <div className="space-y-6">
          <div className="glass-panel p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <h2 className="text-xl font-bold text-surface-900">{memo.title}</h2>
              <p className="text-xs text-surface-500 mt-1">
                Memo ID: {memo.id} · Type: {memo.memo_type} · Status:{" "}
                <span className="badge-neutral">{memo.status}</span>
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleExport("markdown")}
                className="flex items-center gap-1.5 px-3 py-1.5 border border-surface-200 rounded-lg text-sm text-surface-600 hover:bg-surface-50"
                type="button"
              >
                <FileDown className="w-4 h-4" />
                Export Markdown
              </button>
              <button
                onClick={() => handleExport("json")}
                className="flex items-center gap-1.5 px-3 py-1.5 border border-surface-200 rounded-lg text-sm text-surface-600 hover:bg-surface-50"
                type="button"
              >
                <FileDown className="w-4 h-4" />
                Export JSON
              </button>
            </div>
          </div>

          {/* Export View if requested */}
          {exportFormat && exportQuery.data && (
            <div className="glass-panel p-6">
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-sm font-semibold text-surface-800">Exported Content ({exportFormat})</h3>
                <button
                  onClick={() => setExportFormat(null)}
                  className="text-xs text-surface-400 hover:text-surface-600"
                  type="button"
                >
                  Close Export
                </button>
              </div>
              <pre className="p-4 bg-surface-950 text-surface-100 rounded-lg overflow-x-auto text-xs font-mono max-h-60">
                {exportQuery.data.exported_content}
              </pre>
            </div>
          )}

          {/* Executive Summary */}
          {memo.executive_summary && (
            <SectionPanel title="Executive Summary">
              <p className="text-sm text-surface-700 leading-relaxed whitespace-pre-wrap">
                {memo.executive_summary}
              </p>
            </SectionPanel>
          )}

          {/* Sections List */}
          {memo.sections.length > 0 &&
            memo.sections
              .sort((a, b) => a.section_order - b.section_order)
              .map((section) => (
                <SectionPanel
                  key={section.id}
                  title={section.section_name}
                  badge={
                    section.citations.length > 0 ? (
                      <span className="badge-info">{section.citations.length} Citations</span>
                    ) : undefined
                  }
                >
                  <div className="space-y-4">
                    <p className="text-sm text-surface-700 leading-relaxed whitespace-pre-wrap">
                      {section.content}
                    </p>

                    {/* Citations block */}
                    {section.citations.length > 0 && (
                      <div className="pt-4 border-t border-surface-100 space-y-2">
                        <span className="text-xs font-semibold uppercase tracking-wider text-surface-400 block">
                          Verified References
                        </span>
                        <div className="flex flex-wrap gap-2">
                          {section.citations.map((cite, i) => (
                            <CitationBadge
                              key={i}
                              sectionName={cite.section_name}
                              pageNumber={cite.page_number}
                              sourceType={cite.source_type}
                              onClick={() => {
                                if (cite.text_snippet) {
                                  alert(`Context snippet:\n\n"${cite.text_snippet}"`);
                                }
                              }}
                            />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </SectionPanel>
              ))}
        </div>
      )}
    </div>
  );
}
