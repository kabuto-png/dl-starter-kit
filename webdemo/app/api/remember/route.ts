import { NextRequest, NextResponse } from "next/server";
import { akcRemember, type RememberRequest } from "@/lib/akc";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

interface RememberRequestBody {
  task_context: string;
  outcome: string;
  patterns_used: string[];
  success: boolean;
  tags?: string[];
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  let body: RememberRequestBody;

  try {
    body = (await req.json()) as RememberRequestBody;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { task_context, outcome, patterns_used, success, tags } = body;

  if (!task_context || typeof task_context !== "string") {
    return NextResponse.json(
      { error: "task_context is required" },
      { status: 400 }
    );
  }
  if (!outcome || typeof outcome !== "string") {
    return NextResponse.json(
      { error: "outcome is required" },
      { status: 400 }
    );
  }
  if (!Array.isArray(patterns_used)) {
    return NextResponse.json(
      { error: "patterns_used must be an array" },
      { status: 400 }
    );
  }

  const rememberReq: RememberRequest = {
    task_context,
    outcome,
    patterns_used,
    success: Boolean(success),
    tags,
  };

  try {
    const result = await akcRemember(rememberReq);
    return NextResponse.json(result, { status: 202 });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { error: `AKC remember failed: ${message}` },
      { status: 502 }
    );
  }
}
