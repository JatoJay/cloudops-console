import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

async function proxy(request: Request, context: { params: Promise<{ path: string[] }> }) {
  const accessToken = (await cookies()).get("insforge_access_token")?.value;
  if (!accessToken) return NextResponse.json({ message: "Authentication required" }, { status: 401 });
  const { path } = await context.params;
  const response = await fetch(`${backendUrl}/api/${path.join("/")}`, {
    method: request.method,
    headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
    body: ["POST", "PATCH", "PUT"].includes(request.method) ? await request.text() : undefined,
    cache: "no-store",
    signal: AbortSignal.timeout(30_000),
  });
  return new NextResponse(await response.text(), {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json" },
  });
}

export const GET = proxy;
export const POST = proxy;
export const DELETE = proxy;
