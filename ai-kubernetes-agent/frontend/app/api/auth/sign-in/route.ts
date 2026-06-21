import { createAuthActions } from "@insforge/sdk/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function POST(request: NextRequest) {
  const response = NextResponse.json({ ok: true });
  const auth = createAuthActions({
    requestCookies: request.cookies,
    responseCookies: response.cookies,
  });
  const { email, password } = await request.json();
  const { data, error } = await auth.signInWithPassword({ email, password });

  if (error || !data?.user) {
    const status = error?.statusCode ?? 401;
    const message = status === 429
      ? "Too many sign-in attempts. Please wait and try again."
      : status === 403
        ? "Verify your email before signing in."
      : status === 400 || status === 401
        ? "Email or password is incorrect."
        : "Authentication is temporarily unavailable.";
    return NextResponse.json(
      { message },
      { status },
    );
  }

  return response;
}
