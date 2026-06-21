import { createAuthActions } from "@insforge/sdk/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function POST(request: NextRequest) {
  const response = NextResponse.json({ ok: true });
  const auth = createAuthActions({
    requestCookies: request.cookies,
    responseCookies: response.cookies,
  });
  const { email, password } = await request.json();
  const { data, error } = await auth.signUp({ email, password });

  if (error || !data) {
    return NextResponse.json(
      { message: error?.message ?? error?.error ?? "Account creation failed" },
      { status: error?.statusCode ?? 400 },
    );
  }

  return NextResponse.json(
    {
      user: data.user ? { id: data.user.id, email: data.user.email } : null,
      requiresEmailVerification: data.requireEmailVerification ?? !data.user?.emailVerified,
    },
    { headers: response.headers },
  );
}
