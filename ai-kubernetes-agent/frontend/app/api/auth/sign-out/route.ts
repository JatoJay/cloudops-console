import { createAuthActions } from "@insforge/sdk/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function POST(request: NextRequest) {
  const response = NextResponse.json({ ok: true });
  const auth = createAuthActions({
    requestCookies: request.cookies,
    responseCookies: response.cookies,
  });
  const { error } = await auth.signOut();

  if (error) {
    return NextResponse.json({ message: error.message }, { status: error.statusCode ?? 500 });
  }
  return response;
}
