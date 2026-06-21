import { useState, useRef, useEffect } from "react";
import EmptyState from "@/components/EmptyState";
import CitationBadge from "@/components/CitationBadge";
import { useThreads, useMessages, useSendMessage, useCreateThread } from "@/hooks/useAgent";
import { useReports } from "@/hooks/useReports";
import type { Message } from "@/types/api";
import { Send, Plus, MessageSquare, Terminal, HelpCircle, X, Info, Sparkles, AlertTriangle } from "lucide-react";
import { clsx } from "clsx";
import Button from "@/design-system/components/Button";
import Skeleton from "@/design-system/components/Skeleton";

/** Detect LLM-level generation errors returned as apology strings in content */
const isLLMError = (content: string) =>
  content.startsWith("I apologize, but I encountered an error generating the final response");

export default function AgentPage() {
  const { data: threads, isLoading: threadsLoading, isError: threadsError } = useThreads();
  const [activeThreadId, setActiveThreadId] = useState("");

  const { data: messages, isLoading: messagesLoading } = useMessages(
    activeThreadId || undefined,
  );
  const sendMessageMutation = useSendMessage();
  const createThreadMutation = useCreateThread();

  // Load filings reports context
  const { data: reportsData } = useReports(20, 0);
  const reports = reportsData?.items ?? [];
  const [selectedReportId, setSelectedReportId] = useState("");

  const [query, setQuery] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Citation modal inspector state
  const [activeCitation, setActiveCitation] = useState<{
    sectionName?: string;
    pageNumber?: number;
    sourceType?: string;
    sourceText?: string;
  } | null>(null);

  // Auto scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Determine active report and company
  const activeReport = reports.find((r) => r.id === selectedReportId) || reports[0];
  const activeCompanyId = activeReport?.company_id || undefined;
  const activeReportId = activeReport?.id || undefined;

  const handleCreateThread = async () => {
    try {
      const res = await createThreadMutation.mutateAsync(activeCompanyId);
      setActiveThreadId(res.thread_id);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSend = async (e?: React.FormEvent, customQuery?: string) => {
    if (e) e.preventDefault();
    const queryToSend = customQuery ?? query;
    if (!queryToSend.trim() || !activeThreadId) return;

    if (!customQuery) {
      setQuery("");
    }

    try {
      await sendMessageMutation.mutateAsync({
        query: queryToSend,
        thread_id: activeThreadId,
        company_id: activeCompanyId,
        report_id: activeReportId,
      });
    } catch (err) {
      console.error(err);
    }
  };


  // Agent quick query presets
  const presets = [
    {
      label: "Summarize major risk indicators",
      query: "Give me a detailed breakdown of the primary risk factors mentioned across the filed reports."
    },
    {
      label: "Contrast capital allocation models",
      query: "Can you compare the capital allocation strategy and dividend payout plans between Apple and Tesla?"
    },
    {
      label: "Analyze management discussion tone",
      query: "What is the overall sentiment trend in the latest management discussion segments? Is there hedging language?"
    }
  ];

  return (
    <div className="h-[calc(100vh-4rem)] flex gap-4 animate-slide-up">
      {/* Sidebar Threads List */}
      <div className="w-72 shrink-0 flex flex-col glass-panel overflow-hidden bg-white border border-surface-200 shadow-sm">
        <div className="p-4 border-b border-surface-150 flex items-center justify-between bg-surface-50/50">
          <h3 className="font-bold text-surface-800 text-xs flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-brand-650" />
            Linguistic Analyser Sessions
          </h3>
          <button
            onClick={handleCreateThread}
            className="p-1.5 rounded-lg text-surface-500 hover:bg-surface-100 hover:text-surface-900 transition-colors"
            title="Start new analysis session"
            type="button"
          >
            <Plus className="w-4.5 h-4.5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-1 bg-surface-50/20">
          {threadsLoading && (
            <div className="space-y-2">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          )}
          {threadsError && (
            <div className="p-3 text-xs text-danger-dark bg-danger-light/20 rounded border border-danger-250">
              Error fetching analyst sessions.
            </div>
          )}

          {!threadsLoading && !threadsError && threads?.length === 0 && (
            <div className="p-6 text-center text-xs text-surface-450 italic">
              No active session threads. Click the '+' button to start a new chat.
            </div>
          )}

          {threads?.map((t) => (
            <button
              key={t.thread_id}
              onClick={() => setActiveThreadId(t.thread_id)}
              className={clsx(
                "w-full text-left px-3 py-2.5 rounded-lg text-xs font-semibold transition-all truncate block border",
                activeThreadId === t.thread_id
                  ? "bg-brand-50 border-brand-200 text-brand-700 shadow-sm"
                  : "text-surface-650 hover:bg-white hover:border-surface-200 border-transparent"
              )}
              type="button"
            >
              Session: <span className="font-mono text-[10px]">{t.thread_id.slice(0, 12)}…</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Chat Interface */}
      <div className="flex-1 flex flex-col glass-panel overflow-hidden bg-white border border-surface-200 shadow-sm relative">
        {!activeThreadId ? (
          <EmptyState
            title="Interactive Analyst Terminal"
            description="Initiate a linguistic reasoning thread to query structural elements from filings."
            icon={<Terminal className="w-8 h-8 text-brand-650" />}
            action={
              <Button
                onClick={handleCreateThread}
                variant="primary"
                className="flex items-center gap-1.5"
              >
                <Plus className="w-4 h-4" />
                Initialize New Thread
              </Button>
            }
          />
        ) : (
          <>
            <div className="px-6 py-4 border-b border-surface-150 flex justify-between items-center bg-white shadow-sm">
              <div className="flex items-center gap-3">
                <div className="w-2.5 h-2.5 rounded-full bg-success animate-pulse shrink-0" />
                <div>
                  <h3 className="font-bold text-surface-900 text-sm">
                    Active Session: <span className="font-mono text-xs">{activeThreadId}</span>
                  </h3>
                  <p className="text-[10px] text-surface-450 mt-0.5 font-medium">
                    Securities reasoning node executing with citation matching
                  </p>
                </div>
              </div>
              {reports.length > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-surface-500">Query Focus:</span>
                  <select
                    value={selectedReportId}
                    onChange={(e) => setSelectedReportId(e.target.value)}
                    className="text-xs border border-surface-200 rounded-lg px-2.5 py-1.5 bg-white text-surface-700 focus:ring-2 focus:ring-brand-500 focus:outline-none font-medium max-w-[280px] truncate"
                    aria-label="Select report"
                  >
                    {reports.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.report_type} {r.year}{r.quarter ? ` Q${r.quarter}` : ""} &mdash; {r.original_filename?.slice(0, 25)}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {/* Message History */}
            <div className="flex-1 overflow-y-auto p-6 space-y-5 bg-surface-50/20">
              {messagesLoading && (
                <div className="space-y-4">
                  <div className="flex gap-3 max-w-[70%]">
                    <div className="h-10 w-10 rounded-full bg-surface-200 shrink-0" />
                    <Skeleton className="h-16 w-full rounded-xl" />
                  </div>
                  <div className="flex gap-3 max-w-[70%] ml-auto justify-end">
                    <Skeleton className="h-12 w-80 rounded-xl" />
                  </div>
                </div>
              )}

              {messages?.length === 0 && !sendMessageMutation.isPending && (
                <div className="max-w-2xl mx-auto py-8 space-y-6">
                  <div className="text-center space-y-2">
                    <div className="inline-flex items-center justify-center p-3 rounded-full bg-brand-50 text-brand-600 mb-2">
                      <Sparkles className="w-6 h-6" />
                    </div>
                    <h4 className="text-sm font-bold text-surface-800">Choose a Prescribed Query Prompt</h4>
                    <p className="text-xs text-surface-500">
                      Query the LLM agent using preset templates, or type a custom question below.
                    </p>
                  </div>
                  
                  <div className="grid gap-3">
                    {presets.map((preset, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          setQuery(preset.query);
                          handleSend(undefined, preset.query);
                        }}
                        className="flex items-start gap-3 p-4 rounded-xl border border-surface-200 bg-white hover:border-brand-350 hover:bg-brand-50/10 transition-all text-left shadow-sm group"
                        type="button"
                      >
                        <HelpCircle className="w-5 h-5 text-brand-600 mt-0.5 group-hover:scale-105 transition-transform shrink-0" />
                        <div>
                          <span className="text-xs font-bold text-surface-900 block group-hover:text-brand-700 transition-colors">
                            {preset.label}
                          </span>
                          <span className="text-xs text-surface-550 block mt-1 line-clamp-1">
                            {preset.query}
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages?.map((msg: Message) => {
                const isUser = msg.role === "user";
                const citations = (msg.metadata?.citations as any[]) || [];
                const hasLLMError = !isUser && isLLMError(msg.content);

                return (
                  <div
                    key={msg.id}
                    className={clsx(
                      "flex flex-col max-w-[80%] rounded-2xl px-5 py-3.5 text-sm animate-fade-in shadow-sm border",
                      isUser
                        ? "self-end bg-brand-600 border-brand-700 text-white ml-auto rounded-tr-none"
                        : hasLLMError
                          ? "self-start bg-amber-50 border-amber-200 text-amber-800 rounded-tl-none"
                          : "self-start bg-white border-surface-200 text-surface-850 rounded-tl-none"
                    )}
                  >
                    {hasLLMError ? (
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                        <div>
                          <p className="font-bold text-amber-800 text-xs">LLM Quota Limit Reached</p>
                          <p className="text-xs text-amber-700 mt-1 leading-relaxed">
                            The Gemini AI model has reached its free-tier request quota. Evidence was retrieved successfully but the final answer could not be generated. Please wait a moment and try again.
                          </p>
                          <p className="text-[10px] text-amber-600/70 mt-2 font-mono">
                            Error: RESOURCE_EXHAUSTED (429) — gemini-2.5-pro
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="whitespace-pre-wrap leading-relaxed font-sans">{msg.content}</div>
                    )}

                    {/* Citations block if any */}
                    {!isUser && !hasLLMError && citations.length > 0 && (
                      <div className="mt-4 pt-3.5 border-t border-surface-150 space-y-2">
                        <span className="text-[9px] font-bold text-surface-450 uppercase tracking-wider block">
                          Verified References ({citations.length})
                        </span>
                        <div className="flex flex-wrap gap-2">
                          {citations.map((c, i) => (
                            <CitationBadge
                              key={i}
                              sectionName={c.section_name}
                              pageNumber={c.page_number}
                              sourceType={c.source_type}
                              onClick={() => {
                                setActiveCitation({
                                  sectionName: c.section_name,
                                  pageNumber: c.page_number,
                                  sourceType: c.source_type,
                                  sourceText: c.source_text ?? c.text_snippet,
                                });
                              }}
                            />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Generating response message loading shimmer */}
              {sendMessageMutation.isPending && (
                <div className="flex flex-col max-w-[70%] rounded-2xl px-5 py-4 bg-white border border-surface-200 self-start rounded-tl-none space-y-2.5 shadow-sm">
                  <div className="flex items-center gap-2 text-brand-600">
                    <div className="w-2 h-2 bg-brand-600 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <div className="w-2 h-2 bg-brand-600 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <div className="w-2 h-2 bg-brand-600 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                  <Skeleton className="h-3 w-4/5" />
                  <Skeleton className="h-3 w-3/5" />
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>

            {/* Input Form */}
            <form
              onSubmit={(e) => handleSend(e)}
              className="p-4 border-t border-surface-150 bg-white flex gap-3 shadow-md"
            >
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask the analyst agent about SEC filings, risk factors, or comparisons…"
                className="flex-1 text-sm border border-surface-200 rounded-xl px-4 py-3 bg-white text-surface-850 placeholder-surface-450 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all shadow-inner"
                disabled={sendMessageMutation.isPending}
              />
              <Button
                type="submit"
                disabled={!query.trim() || sendMessageMutation.isPending}
                variant="primary"
                className="rounded-xl px-4 h-[44px]"
                aria-label="Send query"
              >
                <Send className="w-4 h-4" />
              </Button>
            </form>
          </>
        )}
      </div>

      {/* Citation Inspector Drawer */}
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
                  {activeCitation.sourceText ? (
                    `"${activeCitation.sourceText}"`
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
