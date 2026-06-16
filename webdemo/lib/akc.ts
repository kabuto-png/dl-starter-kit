/**
 * AKC REST client — typed fetch helpers for Agent Knowledge Core.
 * All calls are server-side only; AKC_BACKEND_URL is never exposed to the browser.
 */

const AKC_BASE = process.env.AKC_BACKEND_URL ?? "";

if (!AKC_BASE && typeof window === "undefined") {
  console.warn("[akc] AKC_BACKEND_URL is not set");
}

// ── Types ──────────────────────────────────────────────────────────────────

export type PatternTier = "gold" | "production" | "experimental";

export interface AkcPattern {
  id: string;
  what_worked: string;
  what_failed: string;
  confidence: number;
  tier: PatternTier;
  times_applied: number;
  tags: string[];
  last_updated: string;
  relevance_score: number;
}

export interface RecallRequest {
  task_context: string;
  tags?: string[];
  top_k?: number;
}

export interface RecallResponse {
  patterns: AkcPattern[];
  total_found: number;
  query_ms: number;
}

export interface RememberRequest {
  task_context: string;
  outcome: string;
  patterns_used: string[];
  success: boolean;
  tags?: string[];
}

export interface RememberResponse {
  status: string;
  pattern_id?: string;
}

export interface HealthResponse {
  status: string;
  pattern_count: number;
  by_tier?: Record<PatternTier, number>;
}

// ── Helpers ────────────────────────────────────────────────────────────────

async function akcFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  if (!AKC_BASE) {
    throw new Error("AKC_BACKEND_URL environment variable is not configured");
  }

  const url = `${AKC_BASE.replace(/\/$/, "")}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`AKC ${path} → ${res.status}: ${body}`);
  }

  return res.json() as Promise<T>;
}

// ── Public API ─────────────────────────────────────────────────────────────

export async function akcHealth(): Promise<HealthResponse> {
  return akcFetch<HealthResponse>("/health");
}

export async function akcRecall(req: RecallRequest): Promise<RecallResponse> {
  return akcFetch<RecallResponse>("/recall", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function akcRemember(
  req: RememberRequest
): Promise<RememberResponse> {
  return akcFetch<RememberResponse>("/remember", {
    method: "POST",
    body: JSON.stringify(req),
  });
}
