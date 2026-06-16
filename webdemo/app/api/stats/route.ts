import { NextResponse } from "next/server";
import { akcHealth } from "@/lib/akc";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(): Promise<NextResponse> {
  try {
    const health = await akcHealth();
    return NextResponse.json(health, { status: 200 });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { error: `AKC health check failed: ${message}` },
      { status: 502 }
    );
  }
}
