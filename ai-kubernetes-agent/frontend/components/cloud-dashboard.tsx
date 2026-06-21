"use client";

import { ArrowLeft, ArrowRight, CloudArrowDown, Sparkle, WarningCircle } from "@phosphor-icons/react";
import Link from "next/link";
import { useState } from "react";

import { CostProgress } from "@/components/cost-progress";
import { useCostAnalysis } from "@/hooks/use-cost-analysis";

export function CloudDashboard({ userId }: { userId: string }) {
  const [selectedGroup, setSelectedGroup] = useState("");
  const { resourceGroups, history, analysis, progress } = useCostAnalysis(userId);
  const activeGroup = selectedGroup || resourceGroups.data?.resource_groups[0] || "";

  const lastRun = history.data?.[0];

  return (
    <div className="mx-auto max-w-7xl px-5 py-9 sm:px-8 lg:px-12 lg:py-12">
      <Link href="/" className="mb-7 inline-flex items-center gap-2 text-sm font-bold text-muted transition hover:text-action"><ArrowLeft size={17} /> Back to tools</Link>
      <section className="grid gap-8 border-b border-line pb-10 lg:grid-cols-[minmax(0,1fr)_380px] lg:gap-16">
        <div className="flex flex-col justify-center">
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-action">GCP cost analysis</p>
          <h1 className="mt-4 max-w-3xl text-5xl font-extrabold leading-[1.01] tracking-[-0.06em] sm:text-7xl">Find the spend hiding in plain sight.</h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-muted">Scan a cloud resource group, surface waste and pricing mismatches, then leave with commands your team can review and run.</p>

          <div className="mt-9 max-w-2xl border-l-2 border-action bg-white/80 px-5 py-5 sm:px-6">
            <label htmlFor="resource-group" className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">Cloud resource group</label>
            <div className="mt-2 flex flex-col gap-3 sm:flex-row">
              <select
                id="resource-group"
                value={activeGroup}
                onChange={(event) => setSelectedGroup(event.target.value)}
                disabled={resourceGroups.isLoading || analysis.isPending}
                className="h-14 min-w-0 flex-1 border border-line bg-white px-4 font-bold text-ink outline-none focus:border-action focus:ring-4 focus:ring-action/10 disabled:text-muted"
              >
                {!resourceGroups.data?.resource_groups.length ? <option value="">No resource groups available</option> : null}
                {resourceGroups.data?.resource_groups.map((group) => <option key={group} value={group}>{group}</option>)}
              </select>
              <button
                type="button"
                disabled={!activeGroup || analysis.isPending}
                onClick={() => analysis.mutate(activeGroup)}
                className="inline-flex min-h-14 items-center justify-center gap-3 bg-action px-7 font-extrabold text-white transition hover:bg-[#075bd9] focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-action/30 disabled:cursor-wait disabled:opacity-55"
              >
                {analysis.isPending ? "Analyzing…" : "Run Analysis"}
                {!analysis.isPending ? <ArrowRight size={19} weight="bold" /> : null}
              </button>
            </div>
            {resourceGroups.isError ? <p className="mt-3 text-sm font-medium text-red-700">Could not load cloud resource groups. Check the active GCP project and try again.</p> : null}
          </div>

          {analysis.isError ? (
            <div className="mt-5 flex max-w-2xl items-start gap-3 border-l-2 border-red-600 bg-red-50/80 px-5 py-4 text-sm text-red-800" role="alert">
              <WarningCircle className="mt-0.5 shrink-0" size={20} weight="fill" />
              <span>{analysis.error.message}</span>
            </div>
          ) : null}
        </div>

        <aside className="border border-line bg-white/85 p-6" aria-labelledby="progress-title">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-action">Live pipeline</p>
              <h2 id="progress-title" className="mt-2 text-lg font-extrabold">Analysis progress</h2>
            </div>
            <span className={`size-2.5 rounded-full ${analysis.isPending ? "animate-pulse bg-action" : "bg-line"}`} aria-hidden />
          </div>
          <CostProgress progress={progress} isRunning={analysis.isPending} />
        </aside>
      </section>

      <section className="grid gap-px border-b border-line bg-line md:grid-cols-3" aria-label="Cost analysis overview">
        <div className="bg-canvas px-5 py-7 md:px-7">
          <CloudArrowDown size={24} className="text-action" />
          <p className="mt-5 font-mono text-[10px] uppercase tracking-[0.15em] text-muted">Provider boundary</p>
          <p className="mt-2 text-lg font-extrabold">GCP project inventory</p>
        </div>
        <div className="bg-canvas px-5 py-7 md:px-7">
          <Sparkle size={24} className="text-action" />
          <p className="mt-5 font-mono text-[10px] uppercase tracking-[0.15em] text-muted">Last scan</p>
          <p className="mt-2 text-lg font-extrabold">{lastRun ? `${lastRun.issues_found} issues found` : "Ready for first analysis"}</p>
        </div>
        <div className="bg-canvas px-5 py-7 md:px-7">
          <p className="font-mono text-4xl font-bold tracking-[-0.06em] text-ink">{history.data?.length ?? 0}</p>
          <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.15em] text-muted">Saved analyses</p>
          <Link href="/cost-analysis/history" className="mt-2 inline-flex items-center gap-2 text-sm font-bold text-action hover:underline">Review cost history <ArrowRight size={14} /></Link>
        </div>
      </section>
    </div>
  );
}
