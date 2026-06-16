import { NextRequest, NextResponse } from "next/server";
import { akcRecall, type AkcPattern } from "@/lib/akc";
import { chatCompletion, type ChatMessage } from "@/lib/gemma";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// ── Request / Response types ───────────────────────────────────────────────

interface ChatRequestBody {
  messages: Array<{ role: "user" | "assistant"; content: string }>;
  tags?: string[];
}

interface ChatResponseBody {
  content: string;
  patterns_used: string[];
  recall_query: {
    task_context: string;
    tags: string[];
    top_k: number;
  };
  recall_ms: number;
  llm_model: string;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function buildSystemPrompt(patterns: AkcPattern[]): string {
  if (patterns.length === 0) {
    return `You are an ASO Specialist assistant at VNG Publishing.
No relevant team-memory patterns were found for this query.
Answer based on general ASO best practices and clearly state that no stored patterns were matched.`;
  }

  const patternJson = JSON.stringify(
    patterns.map((p) => ({
      id: p.id,
      tier: p.tier,
      confidence: p.confidence,
      what_worked: p.what_worked,
      what_failed: p.what_failed,
      tags: p.tags,
    })),
    null,
    2
  );

  return `You are an ASO Specialist assistant at VNG Publishing. The team uses a shared memory system (AKC) to store proven strategies.

Use these team-memory patterns to inform your answer:
<patterns>
${patternJson}
</patterns>

Instructions:
- Cite relevant pattern IDs using the format [pat:ID] when referencing them.
- If a pattern's confidence is below 0.6, note that it is experimental.
- If the patterns don't fully address the question, say so and supplement with general knowledge.
- Be concise and actionable. Prioritize Gold > Production > Experimental tier patterns.`;
}

function extractPatternIds(
  content: string,
  patterns: AkcPattern[]
): string[] {
  const cited: string[] = [];
  for (const p of patterns) {
    // Match [pat:ID] citations or bare ID mentions
    if (content.includes(p.id) || content.includes(`[pat:${p.id}]`)) {
      cited.push(p.id);
    }
  }
  // If none cited explicitly, return all recalled pattern IDs as "used"
  return cited.length > 0 ? cited : patterns.map((p) => p.id);
}

// ── Route handler ──────────────────────────────────────────────────────────

export async function POST(req: NextRequest): Promise<NextResponse> {
  let body: ChatRequestBody;

  try {
    body = (await req.json()) as ChatRequestBody;
  } catch {
    return NextResponse.json(
      { error: "Invalid JSON body" },
      { status: 400 }
    );
  }

  const { messages, tags = [] } = body;

  if (!Array.isArray(messages) || messages.length === 0) {
    return NextResponse.json(
      { error: "messages array is required and must not be empty" },
      { status: 400 }
    );
  }

  const userMessage = [...messages].reverse().find((m) => m.role === "user");
  if (!userMessage) {
    return NextResponse.json(
      { error: "No user message found in messages array" },
      { status: 400 }
    );
  }

  const taskContext = userMessage.content.trim();
  const recallQuery = { task_context: taskContext, tags, top_k: 5 };

  // Step 1: Recall from AKC
  const recallStart = Date.now();
  let recallResult;
  try {
    recallResult = await akcRecall(recallQuery);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { error: `AKC recall failed: ${message}` },
      { status: 502 }
    );
  }
  const recall_ms = Date.now() - recallStart;

  // Step 2: Build messages for LLM
  const systemPrompt = buildSystemPrompt(recallResult.patterns);
  const llmMessages: ChatMessage[] = [
    { role: "system", content: systemPrompt },
    // Include conversation history (skip system-level messages if any)
    ...messages.map((m) => ({
      role: m.role as "user" | "assistant",
      content: m.content,
    })),
  ];

  // Step 3: Call Gemma
  let completion;
  try {
    completion = await chatCompletion({ messages: llmMessages });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { error: `LLM call failed: ${message}` },
      { status: 502 }
    );
  }

  // Step 4: Identify which patterns were cited
  const patterns_used = extractPatternIds(
    completion.content,
    recallResult.patterns
  );

  const responseBody: ChatResponseBody = {
    content: completion.content,
    patterns_used,
    recall_query: recallQuery,
    recall_ms,
    llm_model: completion.model,
  };

  return NextResponse.json(responseBody, { status: 200 });
}
