"use client";

import { ArrowLeft, ArrowRight, ClockCounterClockwise } from "@phosphor-icons/react";
import Link from "next/link";

import { useAnalysisHistory } from "@/hooks/use-cost-analysis";

export function AnalysisHistory({ userId }: { userId: string }) {
  const history = useAnalysisHistory(userId);

  return (
    <div className="mx-auto max-w-7xl px-5 py-9 sm:px-8 lg:px-12 lg:py-12">
      <Link href="/cost-analysis" className="inline-flex items-center gap-2 text-sm font-bold text-muted transition hover:text-action"><ArrowLeft size={17} /> Back to Cost Analyzer</Link>
      <header className="mt-7 border-b border-line pb-8">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-action">Analysis archive</p>
        <h1 className="mt-3 text-5xl font-extrabold tracking-[-0.055em] sm:text-6xl">Past cost analyses.</h1>
        <p className="mt-4 max-w-xl text-lg leading-8 text-muted">Revisit findings, compare savings estimates, and recover the exact fix commands from any completed run.</p>
      </header>

      <section className="pt-8" aria-label="Analysis history">
        <div className="hidden grid-cols-[1.3fr_1fr_0.7fr_1fr_36px] gap-5 border-b border-line pb-3 font-mono text-[10px] uppercase tracking-[0.14em] text-muted md:grid">
          <span>Resource group</span><span>Date</span><span>Issues</span><span>Estimated savings</span><span />
        </div>
        <div className="divide-y divide-line">
          {history.data?.map((item) => {
            const savings = parseSavings(item.estimated_savings);
            return (
              <Link key={item.id} href={`/analysis/${item.id}`} className="group grid gap-4 py-6 transition hover:bg-white/75 md:grid-cols-[1.3fr_1fr_0.7fr_1fr_36px] md:items-center md:gap-5 md:px-3">
                <div>
                  <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted md:hidden">Resource group</span>
                  <p className="mt-1 font-extrabold text-ink md:mt-0">{item.resource_group}</p>
                  <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.1em] text-ready">{item.status}</p>
                </div>
                <div><span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted md:hidden">Date</span><p className="mt-1 text-sm text-muted md:mt-0">{new Date(item.created_at).toLocaleString()}</p></div>
                <div><span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted md:hidden">Issues</span><p className="mt-1 font-mono text-lg font-bold md:mt-0">{item.issues_found}</p></div>
                <div><span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted md:hidden">Estimated savings</span><p className="mt-1 font-extrabold text-ready md:mt-0">{savings}</p></div>
                <ArrowRight size={18} className="text-muted transition group-hover:translate-x-1 group-hover:text-action" />
              </Link>
            );
          })}
        </div>
        {history.isLoading ? <p className="py-12 text-sm text-muted">Loading analysis history…</p> : null}
        {history.isError ? <p className="py-12 text-sm text-red-700">Analysis history could not be loaded.</p> : null}
        {!history.isLoading && !history.data?.length ? (
          <div className="flex flex-col items-start border-l-2 border-line py-5 pl-5">
            <ClockCounterClockwise size={25} className="text-muted" />
            <p className="mt-3 font-bold">No analyses yet.</p>
            <p className="mt-1 text-sm text-muted">Run your first cloud cost analysis from the dashboard.</p>
            <Link href="/cost-analysis" className="mt-4 text-sm font-bold text-action hover:underline">Go to Cost Analyzer</Link>
          </div>
        ) : null}
      </section>
    </div>
  );
}

function parseSavings(value: string) {
  try {
    const savings = JSON.parse(value) as { monthly: number; currency: string };
    return `${new Intl.NumberFormat(undefined, { style: "currency", currency: savings.currency, maximumFractionDigits: 0 }).format(savings.monthly)}/mo`;
  } catch {
    return value;
  }
}
