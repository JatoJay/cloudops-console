"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

export function LoginScreen() {
  const router = useRouter();
  const [mode, setMode] = useState<"sign-in" | "sign-up">("sign-in");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setIsSubmitting(true);
    const form = new FormData(event.currentTarget);

    try {
      const response = await fetch(`/api/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: form.get("email"), password: form.get("password") }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message ?? (mode === "sign-up" ? "Account creation failed" : "Sign in failed"));
      if (payload.requiresEmailVerification) {
        setMode("sign-in");
        setNotice("Account created. Verify your email, then sign in.");
        return;
      }
      router.refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Authentication failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="console-shell min-h-screen overflow-hidden bg-canvas text-ink">
      <header className="flex h-24 items-center border-b border-line px-6 sm:px-10 lg:px-16">
        <span className="text-xl font-extrabold tracking-[-0.035em] sm:text-2xl">
          CloudOps Console
        </span>
      </header>
      <section className="mx-auto grid min-h-[calc(100vh-6rem)] max-w-7xl items-center gap-16 px-6 py-14 sm:px-10 lg:grid-cols-[1fr_420px] lg:px-16">
        <div className="max-w-2xl">
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-action">Operator access</p>
          <h1 className="mt-5 text-5xl font-extrabold leading-[1.02] tracking-[-0.055em] sm:text-7xl">
            Spend less with evidence.
          </h1>
          <p className="mt-7 max-w-lg text-lg leading-8 text-muted">
            Analyze cloud inventory, follow every live cost-analysis step, and revisit prior savings opportunities.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="border border-line bg-white/80 p-7 shadow-[0_24px_80px_rgba(8,39,84,0.08)] sm:p-9">
          <div className="mb-8 border-l-2 border-action pl-4">
            <h2 className="text-2xl font-extrabold tracking-[-0.04em]">{mode === "sign-up" ? "Create account" : "Sign in"}</h2>
            <p className="mt-1 text-sm text-muted">Use your InsForge account.</p>
          </div>
          <label className="block text-sm font-bold" htmlFor="email">Email</label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            className="mt-2 h-12 w-full border border-line bg-white px-4 outline-none transition focus:border-action focus:ring-4 focus:ring-action/10"
          />
          <label className="mt-5 block text-sm font-bold" htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete={mode === "sign-up" ? "new-password" : "current-password"}
            required
            className="mt-2 h-12 w-full border border-line bg-white px-4 outline-none transition focus:border-action focus:ring-4 focus:ring-action/10"
          />
          {error ? <p className="mt-4 text-sm font-medium text-red-700" role="alert">{error}</p> : null}
          {notice ? <p className="mt-4 text-sm font-medium text-ready" role="status">{notice}</p> : null}
          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-7 h-12 w-full bg-action font-bold text-white transition hover:bg-[#075bd9] focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-action/30 disabled:cursor-wait disabled:opacity-60"
          >
            {isSubmitting ? (mode === "sign-up" ? "Creating account…" : "Signing in…") : (mode === "sign-up" ? "Create account" : "Sign in")}
          </button>
          <button
            type="button"
            onClick={() => { setMode(mode === "sign-in" ? "sign-up" : "sign-in"); setError(null); setNotice(null); }}
            className="mt-5 w-full text-sm font-bold text-action hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-action"
          >
            {mode === "sign-in" ? "New here? Create an account" : "Already have an account? Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
