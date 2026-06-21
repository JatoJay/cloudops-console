"use client";

import { ChartLineUp, ClockCounterClockwise, Gauge, PlugsConnected, SignOut, Stack } from "@phosphor-icons/react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";

export function AppShell({
  user,
  children,
}: {
  user: { email?: string | null };
  children: ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const historyHref = pathname.startsWith("/kubernetes")
    ? "/kubernetes/history"
    : "/cost-analysis/history";
  const connectionsHref = pathname.startsWith("/kubernetes")
    ? "/kubernetes/connect"
    : "/cost-analysis/connect";
  const nav = [
    { href: "/", label: "Home", icon: Gauge },
    { href: "/cost-analysis", label: "Cost Analyzer", icon: ChartLineUp },
    { href: "/kubernetes", label: "Kubernetes", icon: Stack },
    { href: connectionsHref, label: "Connections", icon: PlugsConnected },
    { href: historyHref, label: "History", icon: ClockCounterClockwise },
  ];

  async function signOut() {
    await fetch("/api/auth/sign-out", { method: "POST" });
    router.push("/");
    router.refresh();
  }

  return (
    <main className="console-shell min-h-screen bg-canvas text-ink">
      <header className="sticky top-0 z-30 border-b border-line bg-canvas/95 backdrop-blur">
        <div className="mx-auto flex h-[72px] max-w-7xl items-center justify-between px-5 sm:px-8 lg:px-12">
          <Link href="/" className="flex items-center gap-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-action">
            <span className="grid size-9 place-items-center bg-ink text-white"><ChartLineUp size={21} weight="bold" /></span>
            <span className="hidden sm:block">
              <span className="block text-[15px] font-extrabold leading-none tracking-[-0.03em]">CloudOps Console</span>
              <span className="mt-1 hidden font-mono text-[9px] uppercase tracking-[0.18em] text-muted sm:block">Cloud intelligence</span>
            </span>
          </Link>
          <nav className="flex items-center gap-1" aria-label="Primary navigation">
            {nav.map(({ href, label, icon: Icon }) => {
              const active = label === "History" || label === "Connections"
                ? pathname === href
                : href === "/"
                  ? pathname === "/"
                  : href === "/cost-analysis"
                    ? pathname === href || pathname.startsWith("/analysis/")
                    : pathname === href;
              return (
                <Link
                  key={href}
                  href={href}
                  aria-label={label}
                  className={`inline-flex min-h-10 items-center gap-2 px-2 text-sm font-bold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-action sm:px-3 ${active ? "bg-[#eaf2ff] text-action" : "text-muted hover:bg-white hover:text-ink"}`}
                >
                  <Icon size={17} weight={active ? "fill" : "regular"} />
                  <span className="hidden lg:inline">{label}</span>
                </Link>
              );
            })}
          </nav>
          <div className="flex items-center gap-4">
            <span className="hidden max-w-52 truncate text-xs text-muted lg:block">{user.email}</span>
            <button
              type="button"
              onClick={signOut}
              aria-label="Sign out"
              className="grid size-10 place-items-center text-muted transition hover:bg-white hover:text-action focus-visible:outline focus-visible:outline-2 focus-visible:outline-action"
            >
              <SignOut size={19} />
            </button>
          </div>
        </div>
      </header>
      {children}
    </main>
  );
}
