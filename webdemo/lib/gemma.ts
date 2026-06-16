/**
 * Gemma / OpenAI-compatible chat completion client.
 * Server-only — LLM_API_KEY must never reach the browser.
 */

const LLM_BASE = process.env.LLM_BASE_URL ?? "https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1";
const LLM_MODEL = process.env.LLM_MODEL ?? "google/gemma-4-31b-it";
const LLM_KEY = process.env.LLM_API_KEY ?? "";

// ── Types ──────────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface CompletionRequest {
  messages: ChatMessage[];
  temperature?: number;
  max_tokens?: number;
}

export interface CompletionResponse {
  content: string;
  model: string;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

// ── Implementation ─────────────────────────────────────────────────────────

export async function chatCompletion(
  req: CompletionRequest
): Promise<CompletionResponse> {
  if (!LLM_KEY) {
    throw new Error("LLM_API_KEY environment variable is not configured");
  }

  const url = `${LLM_BASE.replace(/\/$/, "")}/chat/completions`;

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${LLM_KEY}`,
    },
    body: JSON.stringify({
      model: LLM_MODEL,
      messages: req.messages,
      temperature: req.temperature ?? 0.7,
      max_tokens: req.max_tokens ?? 1024,
      stream: false,
    }),
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`LLM API → ${res.status}: ${body}`);
  }

  const data = (await res.json()) as {
    choices: Array<{ message: { content: string } }>;
    model: string;
    usage?: CompletionResponse["usage"];
  };

  const content = data.choices?.[0]?.message?.content ?? "";

  return {
    content,
    model: data.model ?? LLM_MODEL,
    usage: data.usage,
  };
}
