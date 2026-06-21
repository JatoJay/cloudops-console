import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  const accessToken = (await cookies()).get("insforge_access_token")?.value;
  if (!accessToken) return NextResponse.json({ message: "Authentication required" }, { status: 401 });
  try {
    const response = await fetch(`${backendUrl}/api/analyze`, {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
      body: await request.text(),
      signal: AbortSignal.timeout(180_000),
    });
    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json" },
    });
  } catch {
    return NextResponse.json({ detail: "Cost analysis did not complete in time" }, { status: 504 });
  }
}
