import { NextResponse } from "next/server";

const backendUrl =
  process.env.BACKEND_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";

export async function GET() {
  try {
    const response = await fetch(`${backendUrl}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5_000),
    });

    if (!response.ok) {
      return NextResponse.json({ detail: "Backend is unavailable" }, { status: 503 });
    }

    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ detail: "Backend is unavailable" }, { status: 503 });
  }
}
