"use client";

import { useState, useEffect, useRef, useCallback } from "react";

// ── Types ──────────────────────────────────────────────────────────────────

type PatternTier = "gold" | "production" | "experimental";

interface StatsData {
  pattern_count: number;
  by_tier?: Record<PatternTier, number>;
}

interface RecallEntry {
  task_context: string;
  top_pattern_id: string;
  tier: PatternTier;
  timestamp: Date;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  patterns_used?: string[];
  recall_ms?: number;
  feedbackGiven?: "useful" | "failed" | null;
}


// ── Utility ────────────────────────────────────────────────────────────────

function generateId(): string {
  return Math.random().toString(36).slice(2, 10);
}

function tierColor(tier: PatternTier): string {
  switch (tier) {
    case "gold":
      return "bg-yellow-900/40 text-yellow-300 border border-yellow-700/40";
    case "production":
      return "bg-blue-900/40 text-blue-300 border border-blue-700/40";
    case "experimental":
      return "bg-gray-800 text-gray-400 border border-gray-600/40";
  }
}

function tierLabel(tier: PatternTier): string {
  switch (tier) {
    case "gold":
      return "Gold";
    case "production":
      return "Production";
    case "experimental":
      return "Experimental";
  }
}

// ── Sub-components ─────────────────────────────────────────────────────────

function TierBadge({ tier }: { tier: PatternTier }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium ${tierColor(tier)}`}
    >
      {tierLabel(tier)}
    </span>
  );
}

function StatCard({ stats }: { stats: StatsData | null }) {
  const [prevCount, setPrevCount] = useState<number | null>(null);
  const [animating, setAnimating] = useState(false);

  useEffect(() => {
    if (stats && prevCount !== null && stats.pattern_count !== prevCount) {
      setAnimating(true);
      const t = setTimeout(() => setAnimating(false), 500);
      return () => clearTimeout(t);
    }
    if (stats) setPrevCount(stats.pattern_count);
  }, [stats, prevCount]);

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs uppercase tracking-widest text-[#8b949e] font-mono">
          AKC Live Stats
        </span>
        <span
          className={`w-2 h-2 rounded-full ${stats ? "bg-green-400 animate-pulse" : "bg-gray-600"}`}
        />
      </div>

      {stats ? (
        <>
          <div className="flex items-end gap-2 mb-5">
            <span
              className={`text-5xl font-bold font-mono text-[#58a6ff] tabular-nums ${animating ? "count-pulse" : ""}`}
            >
              {stats.pattern_count}
            </span>
            <span className="text-[#8b949e] text-sm mb-1">patterns stored</span>
          </div>

          {stats.by_tier && (
            <div className="grid grid-cols-3 gap-2">
              {(["gold", "production", "experimental"] as PatternTier[]).map(
                (tier) => (
                  <div
                    key={tier}
                    className="flex flex-col items-center gap-1.5 bg-[#0f1117] rounded-lg p-2"
                  >
                    <TierBadge tier={tier} />
                    <span className="text-lg font-mono font-semibold text-[#e6edf3] tabular-nums">
                      {stats.by_tier?.[tier] ?? 0}
                    </span>
                  </div>
                )
              )}
            </div>
          )}
        </>
      ) : (
        <div className="flex items-center gap-2 text-[#8b949e] text-sm">
          <span className="animate-pulse">Loading stats...</span>
        </div>
      )}
    </div>
  );
}

function RecallList({ entries }: { entries: RecallEntry[] }) {
  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 flex-1 min-h-0">
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs uppercase tracking-widest text-[#8b949e] font-mono">
          Recent Recalls
        </span>
      </div>

      {entries.length === 0 ? (
        <p className="text-[#8b949e] text-sm text-center py-6">
          No recalls yet. Ask a question to see patterns matched.
        </p>
      ) : (
        <div className="space-y-3 overflow-y-auto">
          {entries.slice(0, 3).map((entry, i) => (
            <div
              key={i}
              className="bg-[#0f1117] rounded-lg p-3 border border-[#30363d]/60 animate-[fadeIn_0.3s_ease-in-out]"
            >
              <p className="text-xs text-[#8b949e] truncate mb-1.5">
                {entry.task_context}
              </p>
              <div className="flex items-center gap-2">
                <TierBadge tier={entry.tier} />
                <span className="mono text-[#8b949e] text-xs truncate flex-1">
                  {entry.top_pattern_id.slice(0, 16)}…
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MessageBubble({
  msg,
  onFeedback,
}: {
  msg: Message;
  onFeedback: (msgId: string, success: boolean) => void;
}) {
  const isUser = msg.role === "user";

  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"} animate-[fadeIn_0.3s_ease-in-out]`}
    >
      <div
        className={`max-w-[85%] ${isUser ? "bg-[#1c2333] text-[#e6edf3]" : "bg-[#161b22] text-[#e6edf3]"} rounded-xl px-4 py-3 border border-[#30363d]/60`}
      >
        <p className="text-sm leading-relaxed whitespace-pre-wrap">
          {msg.content}
        </p>

        {/* Pattern recall footer for assistant messages */}
        {!isUser && msg.patterns_used && msg.patterns_used.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[#30363d]/60">
            <div className="flex flex-wrap gap-1.5 mb-3">
              <span className="text-xs text-[#8b949e]">
                Patterns recalled:
              </span>
              {msg.patterns_used.map((pid) => (
                <span
                  key={pid}
                  className="mono text-xs bg-[#0f1117] border border-[#30363d] rounded px-1.5 py-0.5 text-[#58a6ff]"
                >
                  {pid.slice(0, 8)}…
                </span>
              ))}
              {msg.recall_ms !== undefined && (
                <span className="text-xs text-[#8b949e]">
                  ({msg.recall_ms}ms)
                </span>
              )}
            </div>

            {/* Feedback buttons */}
            {msg.feedbackGiven === null || msg.feedbackGiven === undefined ? (
              <div className="flex gap-2">
                <button
                  onClick={() => onFeedback(msg.id, true)}
                  className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg bg-green-900/30 hover:bg-green-900/50 text-green-400 border border-green-700/30 transition-colors"
                >
                  <span>✓</span>
                  <span>Mark useful</span>
                </button>
                <button
                  onClick={() => onFeedback(msg.id, false)}
                  className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg bg-red-900/20 hover:bg-red-900/40 text-red-400 border border-red-700/30 transition-colors"
                >
                  <span>✗</span>
                  <span>Mark failed</span>
                </button>
              </div>
            ) : (
              <p className="text-xs text-[#8b949e]">
                {msg.feedbackGiven === "useful"
                  ? "✓ Marked useful — outcome saved to AKC"
                  : "✗ Marked failed — outcome saved to AKC"}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [recallEntries, setRecallEntries] = useState<RecallEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // ── Stats polling ────────────────────────────────────────────────────────

  const fetchStats = useCallback(async () => {
    try {
      const healthRes = await fetch("/api/stats");
      if (healthRes.ok) {
        const data = (await healthRes.json()) as StatsData;
        setStats(data);
      }
    } catch {
      // Stats fetch failure is non-critical; keep showing previous value
    }
  }, []);

  useEffect(() => {
    void fetchStats();
    const interval = setInterval(() => void fetchStats(), 5000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  // ── Auto-scroll ──────────────────────────────────────────────────────────

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // ── Send message ─────────────────────────────────────────────────────────

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    setError(null);
    setInput("");

    const userMsg: Message = {
      id: generateId(),
      role: "user",
      content: trimmed,
    };

    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const history = [...messages, userMsg].map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history }),
      });

      if (!res.ok) {
        const errData = (await res.json().catch(() => ({}))) as {
          error?: string;
        };
        throw new Error(errData.error ?? `HTTP ${res.status}`);
      }

      const data = (await res.json()) as {
        content: string;
        patterns_used: string[];
        recall_query: { task_context: string };
        recall_ms: number;
      };

      const assistantMsg: Message = {
        id: generateId(),
        role: "assistant",
        content: data.content,
        patterns_used: data.patterns_used,
        recall_ms: data.recall_ms,
        feedbackGiven: null,
      };

      setMessages((prev) => [...prev, assistantMsg]);

      // Update recall list
      if (data.patterns_used.length > 0) {
        setRecallEntries((prev) => [
          {
            task_context: data.recall_query.task_context,
            top_pattern_id: data.patterns_used[0],
            tier: "production", // We don't get tier back here; use production as default
            timestamp: new Date(),
          },
          ...prev,
        ]);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  // ── Feedback ─────────────────────────────────────────────────────────────

  const handleFeedback = useCallback(
    async (msgId: string, success: boolean) => {
      const msg = messages.find((m) => m.id === msgId);
      if (!msg || !msg.patterns_used) return;

      // Find the user message that preceded this assistant message
      const msgIndex = messages.findIndex((m) => m.id === msgId);
      const precedingUser =
        msgIndex > 0 ? messages[msgIndex - 1] : null;
      const taskContext = precedingUser?.content ?? msg.content;

      try {
        await fetch("/api/remember", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            task_context: taskContext,
            outcome: success
              ? "User marked response as useful"
              : "User marked response as failed/unhelpful",
            patterns_used: msg.patterns_used,
            success,
          }),
        });

        // Update message feedbackGiven status
        setMessages((prev) =>
          prev.map((m) =>
            m.id === msgId
              ? { ...m, feedbackGiven: success ? "useful" : "failed" }
              : m
          )
        );
      } catch {
        // Feedback fire-and-forget; silent failure is acceptable
      }
    },
    [messages]
  );

  // ── Keyboard handling ─────────────────────────────────────────────────────

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void sendMessage();
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <main className="flex flex-col h-screen bg-[#0f1117]">
      {/* Header */}
      <header className="flex-none border-b border-[#30363d] px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold">
            A
          </div>
          <div>
            <h1 className="text-sm font-semibold text-[#e6edf3]">
              AKC Demo
            </h1>
            <p className="text-xs text-[#8b949e]">
              Agent Knowledge Core — ASO Specialist Memory
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#8b949e] font-mono">
            GreenNode Clawathon 2026
          </span>
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
        </div>
      </header>

      {/* Body: 3-column layout */}
      <div className="flex flex-1 min-h-0 gap-0">
        {/* Left 60%: Chat */}
        <div className="flex flex-col w-[60%] border-r border-[#30363d] min-h-0">
          {/* Message list */}
          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-900/40 to-purple-900/40 border border-[#30363d] flex items-center justify-center text-3xl">
                  🧠
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-[#e6edf3] mb-1">
                    Ask the AKC
                  </h2>
                  <p className="text-sm text-[#8b949e] max-w-md">
                    Ask any ASO question. AKC will recall relevant team-memory
                    patterns and guide Gemma&apos;s response with proven strategies.
                  </p>
                </div>
                <div className="grid grid-cols-1 gap-2 w-full max-w-md mt-2">
                  {[
                    "How should I optimize icon creative for the VN market?",
                    "What PPO test duration is recommended?",
                    "Which metadata changes have highest impact in Japan?",
                  ].map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => setInput(suggestion)}
                      className="text-left text-xs px-3 py-2 rounded-lg bg-[#161b22] hover:bg-[#1c2333] border border-[#30363d] text-[#8b949e] hover:text-[#e6edf3] transition-colors"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                msg={msg}
                onFeedback={handleFeedback}
              />
            ))}

            {/* Thinking indicator */}
            {loading && (
              <div className="flex justify-start animate-[fadeIn_0.3s_ease-in-out]">
                <div className="bg-[#161b22] border border-[#30363d]/60 rounded-xl px-4 py-3 max-w-[60%]">
                  <div className="flex items-center gap-2 text-[#8b949e] text-sm">
                    <span className="animate-pulse">Agent thinking</span>
                    <span className="flex gap-1">
                      <span
                        className="w-1.5 h-1.5 bg-[#8b949e] rounded-full animate-bounce"
                        style={{ animationDelay: "0ms" }}
                      />
                      <span
                        className="w-1.5 h-1.5 bg-[#8b949e] rounded-full animate-bounce"
                        style={{ animationDelay: "150ms" }}
                      />
                      <span
                        className="w-1.5 h-1.5 bg-[#8b949e] rounded-full animate-bounce"
                        style={{ animationDelay: "300ms" }}
                      />
                    </span>
                  </div>
                  <p className="text-xs text-[#8b949e]/60 mt-1">
                    Recalling patterns from AKC + calling Gemma…
                  </p>
                </div>
              </div>
            )}

            {/* Error display */}
            {error && (
              <div className="flex justify-center animate-[fadeIn_0.3s_ease-in-out]">
                <div className="bg-red-900/20 border border-red-700/40 rounded-xl px-4 py-3 max-w-[80%]">
                  <p className="text-sm text-red-400 font-mono">{error}</p>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div className="flex-none border-t border-[#30363d] px-4 py-3">
            <div className="flex gap-3 items-end">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask an ASO question… (Enter to send, Shift+Enter for newline)"
                disabled={loading}
                rows={2}
                className="flex-1 resize-none bg-[#161b22] border border-[#30363d] rounded-xl px-4 py-3 text-sm text-[#e6edf3] placeholder:text-[#484f58] focus:outline-none focus:border-[#58a6ff] transition-colors disabled:opacity-50"
              />
              <button
                onClick={() => void sendMessage()}
                disabled={loading || !input.trim()}
                className="flex-none h-10 px-4 rounded-xl bg-[#1f6feb] hover:bg-[#388bfd] disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
              >
                Send
              </button>
            </div>
          </div>
        </div>

        {/* Right 40%: Stats + Recalls */}
        <div className="flex flex-col w-[40%] p-4 gap-4 min-h-0">
          <StatCard stats={stats} />
          <RecallList entries={recallEntries} />

          {/* Architecture note */}
          <div className="flex-none bg-[#161b22] border border-[#30363d] rounded-xl p-4">
            <p className="text-xs uppercase tracking-widest text-[#8b949e] font-mono mb-2">
              Flow
            </p>
            <div className="flex items-center gap-1.5 text-xs text-[#8b949e]">
              <span className="bg-[#1c2333] rounded px-2 py-1 text-[#58a6ff] font-mono">
                User
              </span>
              <span>→</span>
              <span className="bg-[#1c2333] rounded px-2 py-1 font-mono">
                /api/chat
              </span>
              <span>→</span>
              <span className="bg-[#1c2333] rounded px-2 py-1 font-mono">
                AKC /recall
              </span>
              <span>→</span>
              <span className="bg-[#1c2333] rounded px-2 py-1 font-mono">
                Gemma
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-[#8b949e] mt-1.5">
              <span className="invisible bg-[#1c2333] rounded px-2 py-1 font-mono">
                User
              </span>
              <span>→</span>
              <span className="bg-[#1c2333] rounded px-2 py-1 font-mono">
                Feedback btn
              </span>
              <span>→</span>
              <span className="bg-[#1c2333] rounded px-2 py-1 font-mono">
                AKC /remember
              </span>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
