import { useState } from "react";
import PageHeader from "@/components/PageHeader";
import SectionPanel from "@/components/SectionPanel";
import Skeleton from "@/design-system/components/Skeleton";
import ErrorFallback from "@/design-system/patterns/ErrorFallback";
import EmptyState from "@/components/EmptyState";
import CitationBadge from "@/components/CitationBadge";
import { useReports } from "@/hooks/useReports";
import { useMemoDetails, useGenerateMemo, useMemoExport } from "@/hooks/useMemos";
import { FileText, FileDown, Plus, X, Search, Info } from "lucide-react";
import Button from "@/design-system/components/Button";

export default function MemoPage() {
  const { data: reportsData } = useReports(10, 0);
  const reports = reportsData?.items ?? [];

  const [selectedReportId, setSelectedReportId] = useState("");
  const [memoId, setMemoId] = useState("");
  const [exportFormat, setExportFormat] = useState<"markdown" | "json" | null>(null);
  
  // Custom interactive citation details modal state
  const [activeCitation, setActiveCitation] = useState<{
    sectionName?: string | null;
    pageNumber?: number | null;
    sourceType?: string | null;
    textSnippet?: string | null;
  } | null>(null);

  const reportId = selectedReportId || (reports.length > 0 ? reports[0].id : "");

  const { data: memo, isLoading, isError, refetch } = useMemoDetails(memoId || undefined);
  const generateMutation = useGenerateMemo();
  const exportQuery = useMemoExport(memoId || undefined, exportFormat || "markdown", !!exportFormat);

  const handleGenerate = async () => {
    if (!reportId) return;
    const activeReport = reports.find((r) => r.id === reportId);
    if (!activeReport || !activeReport.company_id) {
      return;
    }

    try {
      const res = await generateMutation.mutateAsync({
        company_id: activeReport.company_id,
        report_id: reportId,
        memo_type: "SINGLE_COMPANY",
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

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton variant="text" className="w-1/3 h-8" />
        <Skeleton variant="card" className="h-20 w-full" />
        <div className="space-y-6">
          <Skeleton variant="memo" />
          <Skeleton variant="memo" />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorFallback
        title="Filing Memo Generation Failure"
        message="Could not synthesise the company investment memorandum records."
        resetErrorBoundary={refetch}
      />
    );
  }

  return (
    <div className="space-y-6 animate-slide-up">
      <PageHeader
        title="Investment Memos"
        subtitle="Generate and review LLM-powered investment analysis with citations"
        actions={
          <div className="flex items-center gap-3">
            <select
              value={selectedReportId}
              onChange={(e) => setSelectedReportId(e.target.value)}
              className="text-sm border border-surface-200 rounded-lg px-3 py-2 bg-white text-surface-700 focus:ring-2 focus:ring-brand-500 focus:outline-none"
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

            <Button
              onClick={handleGenerate}
              disabled={!reportId || generateMutation.isPending}
              variant="primary"
              loading={generateMutation.isPending}
            >
              <Plus className="w-4 h-4 mr-1.5" />
              {generateMutation.isPending ? "Synthesising..." : "Generate Memo"}
            </Button>
          </div>
        }
      />

      {/* Load Existing Memo Section */}
      <div className="glass-panel p-5 flex flex-col sm:flex-row gap-4 items-center bg-white border border-surface-200">
        <span className="text-sm text-surface-700 font-bold whitespace-nowrap flex items-center gap-1.5">
          <Search className="w-4 h-4 text-brand-650" />
          Load Existing Memo:
        </span>
        <input
          type="text"
          placeholder="Paste Memo UUID (e.g. 550e8400-e29b-41d4-a716-446655440000)…"
          value={memoId}
          onChange={(e) => setMemoId(e.target.value)}
          className="text-sm border border-surface-200 rounded-lg px-3 py-2 bg-white w-full focus:ring-2 focus:ring-brand-500 focus:outline-none"
        />
      </div>

      {!memo && (
        <div className="p-8">
          <EmptyState
            title="No investment memo selected"
            description="Choose an indexed filing from the dropdown to run synthesis, or load an existing Memo ID."
            icon={<FileText className="w-7 h-7 text-brand-650" />}
          />
        </div>
      )}

      {memo && (
        <div className="space-y-6">
          <div className="glass-panel p-5 bg-white border border-surface-200 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <h2 className="text-lg font-bold text-surface-900">{memo.title}</h2>
              <p className="text-xs text-surface-500 mt-1">
                Memo ID: <span className="font-mono">{memo.id}</span> · Type: {memo.memo_type} · Status:{" "}
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-brand-50 text-brand-700 font-mono">
                  {memo.status}
                </span>
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => handleExport("markdown")}
                variant="outline"
                className="flex items-center gap-1.5 text-xs"
                disabled={memo.status !== "COMPLETED"}
              >
                <FileDown className="w-4 h-4" />
                Export Markdown
              </Button>
              <Button
                onClick={() => handleExport("json")}
                variant="outline"
                className="flex items-center gap-1.5 text-xs"
                disabled={memo.status !== "COMPLETED"}
              >
                <FileDown className="w-4 h-4" />
                Export JSON
              </Button>
            </div>
          </div>

          {(memo.status === "PENDING" || memo.status === "GENERATING") && (
            <div className="glass-panel p-8 flex flex-col items-center justify-center text-center bg-white border border-surface-200">
              <div className="w-12 h-12 rounded-full border-4 border-brand-200 border-t-brand-600 animate-spin mb-4" />
              <h3 className="text-base font-bold text-surface-900">AI Synthesis in Progress</h3>
              <p className="text-sm text-surface-500 mt-2 max-w-md">
                Our multi-agent reasoning system is parsing the report metrics, risk factors, management sentiment, and cross-company benchmark data to build a comprehensive investment memo. This usually takes 15–30 seconds.
              </p>
            </div>
          )}

          {memo.status === "FAILED" && (
            <div className="glass-panel p-8 flex flex-col items-center justify-center text-center bg-red-50 border border-red-200">
              <div className="text-red-500 text-lg font-bold mb-2">⚠ Generation Failed</div>
              <p className="text-sm text-red-700 max-w-md">
                An error occurred during memo generation. Please verify that the report has finished processing completely and try again.
              </p>
            </div>
          )}

          {/* Export Panel with loading spinner */}
          {exportFormat && (
            <div className="glass-panel p-5 bg-surface-50 border border-surface-200 animate-slide-up">
              <div className="flex justify-between items-center mb-3">
                <span className="text-xs font-bold text-brand-650 uppercase tracking-wider">
                  Export Panel Output ({exportFormat})
                </span>
                <button
                  onClick={() => setExportFormat(null)}
                  className="p-1 rounded-lg text-surface-400 hover:text-surface-650 hover:bg-surface-200/50 transition-colors"
                  type="button"
                  aria-label="Close export panel"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              
              {exportQuery.isLoading ? (
                <div className="space-y-2 py-4">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-4 w-1/2" />
                </div>
              ) : (
                <pre className="p-4 bg-surface-900 text-surface-100 rounded-lg overflow-x-auto text-xs font-mono max-h-60 border border-surface-850">
                  {exportQuery.data?.exported_content}
                </pre>
              )}
            </div>
          )}

          {/* Executive Summary */}
          {memo.executive_summary && (
            <SectionPanel title="Executive Summary">
              <p className="text-sm text-surface-750 leading-relaxed whitespace-pre-wrap font-serif">
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
                      <span className="badge-neutral font-mono">{section.citations.length} Citations</span>
                    ) : undefined
                  }
                >
                  <div className="space-y-4">
                    <p className="text-sm text-surface-750 leading-relaxed whitespace-pre-wrap font-serif">
                      {section.content}
                    </p>

                    {/* Citations block */}
                    {section.citations.length > 0 && (
                      <div className="pt-4 border-t border-surface-150 space-y-2.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-surface-450 block">
                          Verified Citations & References
                        </span>
                        <div className="flex flex-wrap gap-2">
                          {section.citations.map((cite, i) => (
                            <CitationBadge
                              key={i}
                              sectionName={cite.section_name}
                              pageNumber={cite.page_number}
                              sourceType={cite.source_type}
                              onClick={() => {
                                setActiveCitation({
                                  sectionName: cite.section_name,
                                  pageNumber: cite.page_number,
                                  sourceType: cite.source_type,
                                  textSnippet: cite.text_snippet,
                                });
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

      {/* Citation Inspector Overlay Panel */}
      {activeCitation && (
        <>
          <div
            className="fixed inset-0 bg-surface-900/40 backdrop-blur-sm z-40 transition-opacity"
            onClick={() => setActiveCitation(null)}
          />

          <div className="fixed inset-y-0 right-0 w-full max-w-lg bg-white shadow-2xl border-l border-surface-200 z-50 animate-slide-in-right overflow-y-auto flex flex-col">
            <div className="p-5 border-b border-surface-150 flex items-center justify-between bg-surface-50/50">
              <div className="flex items-center gap-2">
                <Info className="w-5 h-5 text-brand-650" />
                <div>
                  <span className="text-[10px] font-bold text-brand-600 uppercase tracking-wider">
                    Citation Inspector
                  </span>
                  <h2 className="text-sm font-bold text-surface-900 mt-0.5">
                    Source: {activeCitation.sourceType ?? "Filing Segment"}
                  </h2>
                </div>
              </div>
              <button
                onClick={() => setActiveCitation(null)}
                className="p-1.5 rounded-lg text-surface-400 hover:text-surface-600 hover:bg-surface-100 transition-colors"
                type="button"
                aria-label="Close inspector"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-5 flex-1">
              <div className="grid grid-cols-2 gap-4 p-4 rounded-lg bg-surface-50 border border-surface-200">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-surface-450 block">
                    Section Name
                  </span>
                  <p className="mt-0.5 text-xs font-semibold text-surface-900">
                    {activeCitation.sectionName ?? "General"}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-surface-450 block">
                    Source Page
                  </span>
                  <p className="mt-0.5 text-xs font-semibold text-surface-900">
                    Page {activeCitation.pageNumber ?? "N/A"}
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-surface-450 block">
                  Original Document Segment Text
                </span>
                <div className="p-4 bg-surface-50 border-l-4 border-brand-500 rounded-r-lg font-mono text-xs text-surface-700 leading-relaxed italic">
                  {activeCitation.textSnippet ? (
                    `"${activeCitation.textSnippet}"`
                  ) : (
                    <span className="text-surface-400 italic">No source text segment captured for this citation.</span>
                  )}
                </div>
              </div>
            </div>

            <div className="p-4 border-t border-surface-150 bg-surface-50/50 flex justify-end">
              <button
                type="button"
                onClick={() => setActiveCitation(null)}
                className="px-4 py-2 text-xs font-semibold border border-surface-250 rounded-lg hover:bg-surface-100 text-surface-650 transition-colors"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
