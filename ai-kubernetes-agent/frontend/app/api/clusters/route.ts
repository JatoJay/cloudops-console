import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

export async function GET() {
  const accessToken = (await cookies()).get("insforge_access_token")?.value;
  if (!accessToken) {
    return NextResponse.json({ message: "Authentication required" }, { status: 401 });
  }

  try {
    const response = await fetch(`${backendUrl}/clusters`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json" },
    });
  } catch {
    return NextResponse.json(
      { message: "The cluster service did not respond in time" },
      { status: 504 },
    );
  }
}
