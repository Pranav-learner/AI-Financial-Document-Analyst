import { useState, useRef, useEffect } from "react";
import EmptyState from "@/components/EmptyState";
import CitationBadge from "@/components/CitationBadge";
import { useThreads, useMessages, useSendMessage, useCreateThread } from "@/hooks/useAgent";
import type { Message } from "@/types/api";
import { Send, Plus, MessageSquare } from "lucide-react";
import { clsx } from "clsx";

export default function AgentPage() {

  const { data: threads, isLoading: threadsLoading, isError: threadsError } = useThreads();
  const [activeThreadId, setActiveThreadId] = useState("");

  const { data: messages, isLoading: messagesLoading } = useMessages(
    activeThreadId || undefined,
  );
  const sendMessageMutation = useSendMessage();
  const createThreadMutation = useCreateThread();

  const [query, setQuery] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleCreateThread = async () => {
    try {
      const res = await createThreadMutation.mutateAsync(undefined);
      setActiveThreadId(res.thread_id);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || !activeThreadId) return;

    const currentQuery = query;
    setQuery("");

    try {
      await sendMessageMutation.mutateAsync({
        query: currentQuery,
        thread_id: activeThreadId,
      });
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="h-[calc(100vh-4rem)] flex gap-4 animate-slide-up">
      {/* Sidebar Threads List */}
      <div className="w-64 shrink-0 flex flex-col glass-panel overflow-hidden">
        <div className="p-4 border-b border-surface-100 flex items-center justify-between">
          <h3 className="font-semibold text-surface-800 text-sm flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-surface-400" />
            Chat Sessions
          </h3>
          <button
            onClick={handleCreateThread}
            className="p-1 rounded-md text-surface-500 hover:bg-surface-50 hover:text-surface-800"
            title="New session"
            type="button"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {threadsLoading && <div className="p-3 text-xs text-surface-400">Loading sessions…</div>}
          {threadsError && <div className="p-3 text-xs text-danger">Error loading sessions</div>}

          {!threadsLoading && !threadsError && threads?.length === 0 && (
            <div className="p-3 text-xs text-surface-400 text-center">No active sessions.</div>
          )}

          {threads?.map((t) => (
            <button
              key={t.thread_id}
              onClick={() => setActiveThreadId(t.thread_id)}
              className={clsx(
                "w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-colors truncate block",
                activeThreadId === t.thread_id
                  ? "bg-brand-50 text-brand-700 font-semibold"
                  : "text-surface-600 hover:bg-surface-50 hover:text-surface-900",
              )}
              type="button"
            >
              Session: {t.thread_id.slice(0, 8)}…
            </button>
          ))}
        </div>
      </div>

      {/* Main Chat Interface */}
      <div className="flex-1 flex flex-col glass-panel overflow-hidden">
        {!activeThreadId ? (
          <EmptyState
            title="No session selected"
            description="Select an existing session from the list or start a new chat session to talk to the financial analyst agent."
            action={
              <button
                onClick={handleCreateThread}
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 transition-colors"
                type="button"
              >
                <Plus className="w-4 h-4" />
                New Chat Session
              </button>
            }
          />
        ) : (
          <>
            <div className="px-6 py-4 border-b border-surface-100 flex justify-between items-center bg-white">
              <div>
                <h3 className="font-semibold text-surface-800 text-sm">
                  Session: {activeThreadId}
                </h3>
                <p className="text-[10px] text-surface-400 mt-0.5">
                  Analyst Agent responds using verified documents
                </p>
              </div>
            </div>

            {/* Message History */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messagesLoading && <div className="text-center text-xs text-surface-400">Loading messages…</div>}

              {messages?.map((msg: Message) => {
                const isUser = msg.role === "user";
                // citations might be in msg.metadata
                const citations = (msg.metadata?.citations as any[]) || [];

                return (
                  <div
                    key={msg.id}
                    className={clsx(
                      "flex flex-col max-w-[85%] rounded-xl px-4 py-3 text-sm animate-fade-in",
                      isUser
                        ? "self-end bg-brand-600 text-white ml-auto"
                        : "self-start bg-surface-50 border border-surface-200 text-surface-800",
                    )}
                  >
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>

                    {/* Citations block if any */}
                    {!isUser && citations.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-surface-200/50 space-y-1.5">
                        <span className="text-[10px] font-semibold text-surface-400 uppercase tracking-wider block">
                          Supporting Citations
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {citations.map((c, i) => (
                            <CitationBadge
                              key={i}
                              sectionName={c.section_name}
                              pageNumber={c.page_number}
                              sourceType={c.source_type}
                              onClick={() => {
                                if (c.source_text) {
                                  alert(`Evidence excerpt:\n\n"${c.source_text}"`);
                                }
                              }}
                            />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Form */}
            <form
              onSubmit={handleSend}
              className="p-4 border-t border-surface-100 bg-white flex gap-2"
            >
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask the analyst agent about SEC filings, risk factors, or comparisons…"
                className="flex-1 text-sm border border-surface-200 rounded-lg px-4 py-2.5 bg-white text-surface-800 placeholder-surface-400 focus:outline-none focus:border-brand-500"
                disabled={sendMessageMutation.isPending}
              />
              <button
                type="submit"
                disabled={!query.trim() || sendMessageMutation.isPending}
                className="px-4 py-2.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors flex items-center justify-center"
                aria-label="Send query"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
