import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  const accessToken = (await cookies()).get("insforge_access_token")?.value;
  if (!accessToken) {
    return NextResponse.json({ message: "Authentication required" }, { status: 401 });
  }

  try {
    const response = await fetch(`${backendUrl}/investigate`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: await request.text(),
      signal: AbortSignal.timeout(120_000),
    });

    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json" },
    });
  } catch {
    return NextResponse.json(
      {
        detail: {
          message: "The investigation service did not respond in time.",
          guidance: [
            "Verify that the backend is running.",
            "Check cluster connectivity, then try again.",
          ],
        },
      },
      { status: 504 },
    );
  }
}
