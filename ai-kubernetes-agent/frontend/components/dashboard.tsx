"use client";

import { ArrowLeft, ChartLineUp, CheckCircle, ClockCounterClockwise, House, PlugsConnected, ShieldWarning, SignOut, WarningCircle } from "@phosphor-icons/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { DiagnosisCard } from "@/components/diagnosis-card";
import { ProgressList } from "@/components/progress-list";
import { StatusIndicator } from "@/components/status-indicator";
import { VulnerabilityReport } from "@/components/vulnerability-report";
import { useInvestigation } from "@/hooks/use-investigation";
import { useVulnerabilityScan } from "@/hooks/use-vulnerability-scan";
import { InvestigationApiError } from "@/services/investigations";

export function Dashboard({ user }: { user: { id: string; email?: string | null } }) {
  const router = useRouter();
  const [selectedContext, setSelectedContext] = useState("");
  const { currentStep, activeContext, clusters, investigation } = useInvestigation(user.id, selectedContext);
  const vulnerabilityScan = useVulnerabilityScan(activeContext);

  const investigationError = investigation.error instanceof InvestigationApiError
    ? investigation.error
    : null;

  async function signOut() {
    await fetch("/api/auth/sign-out", { method: "POST" });
    router.refresh();
  }

  return (
    <main className="console-shell min-h-screen bg-canvas text-ink">
      <header className="sticky top-0 z-20 flex h-20 items-center justify-between border-b border-line bg-canvas/90 px-3 backdrop-blur sm:px-8 lg:px-12">
        <div className="flex items-center gap-4">
          <Link href="/kubernetes" className="text-lg font-extrabold tracking-[-0.04em] sm:text-xl"><span className="sm:hidden">K8s</span><span className="hidden sm:inline">Kubernetes Troubleshooter</span></Link>
          <nav className="flex items-center gap-1 border-l border-line pl-3" aria-label="Kubernetes navigation">
            <Link href="/" className="inline-flex min-h-10 items-center gap-2 px-2 text-sm font-bold text-muted transition hover:bg-white hover:text-action sm:px-3"><House size={17} /><span className="hidden md:inline">Main dashboard</span></Link>
            <Link href="/cost-analysis" className="inline-flex min-h-10 items-center gap-2 px-2 text-sm font-bold text-muted transition hover:bg-white hover:text-action sm:px-3"><ChartLineUp size={17} /><span className="hidden md:inline">Cost Analyzer</span></Link>
            <Link href="/kubernetes/history" className="inline-flex min-h-10 items-center gap-2 px-2 text-sm font-bold text-muted transition hover:bg-white hover:text-action sm:px-3"><ClockCounterClockwise size={17} /><span className="hidden md:inline">History</span></Link>
            <Link href="/kubernetes/connect" className="inline-flex min-h-10 items-center gap-2 px-2 text-sm font-bold text-muted transition hover:bg-white hover:text-action sm:px-3"><PlugsConnected size={17} /><span className="hidden md:inline">Connect</span></Link>
          </nav>
        </div>
        <div className="flex items-center gap-4 sm:gap-7">
          <span className="hidden text-sm text-muted lg:block">{user.email}</span>
          <button type="button" onClick={signOut} className="inline-flex items-center gap-2 text-sm font-bold text-ink hover:text-action focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-action">
            <SignOut size={18} /><span className="hidden lg:inline">Sign out</span>
          </button>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-5 py-9 sm:px-8 lg:px-12 lg:py-12">
        <Link href="/" className="mb-7 inline-flex items-center gap-2 text-sm font-bold text-muted transition hover:text-action"><ArrowLeft size={17} /> Back to tools</Link>
        <section className="grid gap-8 border-b border-line pb-10 lg:grid-cols-[1fr_360px] lg:gap-16">
          <div className="flex flex-col justify-center">
            <div className="mb-7"><StatusIndicator /></div>
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-action">On-demand investigation</p>
            <h1 className="mt-4 max-w-3xl text-5xl font-extrabold leading-[1.02] tracking-[-0.055em] sm:text-7xl">Find the failure signal.</h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-muted">Collect cluster evidence, correlate the symptoms, and return a reviewable Kubernetes fix.</p>
            <div className="mt-8 max-w-xl border-l-2 border-action bg-white/70 px-5 py-4">
              <label htmlFor="cluster-context" className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">Kubernetes cluster</label>
              <select
                id="cluster-context"
                value={activeContext}
                onChange={(event) => setSelectedContext(event.target.value)}
                disabled={clusters.isLoading || investigation.isPending || !clusters.data?.contexts.length}
                className="mt-2 h-12 w-full border border-line bg-white px-3 font-bold text-ink outline-none focus:border-action focus:ring-4 focus:ring-action/10 disabled:text-muted"
              >
                {!clusters.data?.contexts.length ? <option value="">No clusters available</option> : null}
                {clusters.data?.contexts.map((context) => <option key={context} value={context}>{context}</option>)}
              </select>
              {clusters.data?.message ? <p className="mt-3 text-sm text-red-700">{clusters.data.message}</p> : null}
              {clusters.data?.guidance.length ? <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-red-700">{clusters.data.guidance.map((item) => <li key={item}>{item}</li>)}</ul> : null}
              {clusters.isError ? <p className="mt-3 text-sm text-red-700">Unable to load Kubernetes clusters.</p> : null}
            </div>
            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                disabled={investigation.isPending || vulnerabilityScan.isPending || !activeContext}
                onClick={() => investigation.mutate()}
                className="min-h-14 min-w-64 bg-action px-8 font-bold text-white transition hover:bg-[#075bd9] focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-action/30 disabled:cursor-wait disabled:opacity-60"
              >
                {investigation.isPending ? "Investigating Kubernetes Cluster…" : "Investigate Cluster"}
              </button>
              <button
                type="button"
                disabled={vulnerabilityScan.isPending || investigation.isPending || !activeContext}
                onClick={() => vulnerabilityScan.mutate()}
                className="inline-flex min-h-14 min-w-60 items-center justify-center gap-3 border border-action bg-white/80 px-6 font-bold text-action transition hover:bg-[#eef5ff] focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-action/30 disabled:cursor-wait disabled:opacity-60"
              >
                <ShieldWarning size={20} weight="bold" />
                {vulnerabilityScan.isPending ? "Scanning Vulnerabilities…" : "Scan Vulnerabilities"}
              </button>
            </div>
            {investigation.isError ? (
              <div className="mt-5 max-w-xl border-l-2 border-red-600 bg-red-50/80 px-5 py-4" role="alert">
                <div className="flex items-center gap-2 font-bold text-red-800"><WarningCircle size={20} weight="fill" />{investigation.error.message}</div>
                {investigationError?.guidance.length ? <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-red-800">{investigationError.guidance.map((item) => <li key={item}>{item}</li>)}</ul> : null}
              </div>
            ) : null}
            {vulnerabilityScan.isError ? (
              <div className="mt-5 max-w-xl border-l-2 border-red-600 bg-red-50/80 px-5 py-4" role="alert">
                <div className="flex items-center gap-2 font-bold text-red-800"><WarningCircle size={20} weight="fill" />{vulnerabilityScan.error.message}</div>
              </div>
            ) : null}
          </div>

          <aside className="border border-line bg-white/75 p-5 sm:p-6" aria-labelledby="progress-title">
            <div className="flex items-center justify-between">
              <h2 id="progress-title" className="font-bold">Investigation status</h2>
              <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Live</span>
            </div>
            <ProgressList currentStep={currentStep} isRunning={investigation.isPending} clusterHealthy={investigation.data?.cluster_healthy} />
          </aside>
        </section>

        <div className="space-y-12 pt-10">
          {vulnerabilityScan.data ? <VulnerabilityReport key={vulnerabilityScan.submittedAt} report={vulnerabilityScan.data} /> : null}
          {investigation.data?.diagnosis ? <DiagnosisCard diagnosis={investigation.data.diagnosis} /> : investigation.data?.cluster_healthy ? (
            <section className="border border-ready/40 bg-[#effaf4] px-6 py-7" aria-live="polite">
              <div className="flex items-center gap-3 text-ready"><CheckCircle size={25} weight="fill" /><h2 className="text-xl font-extrabold text-ink">No critical Kubernetes issues detected.</h2></div>
              <p className="mt-3 pl-9 text-muted">Cluster appears healthy.</p>
            </section>
          ) : investigation.data?.message ? (
            <section className="border-l-2 border-red-600 bg-red-50/70 px-5 py-5" role="status">
              <h2 className="font-bold text-red-800">{investigation.data.message}</h2>
              {investigation.data.guidance.length ? <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-red-800">{investigation.data.guidance.map((item) => <li key={item}>{item}</li>)}</ul> : null}
            </section>
          ) : (
            <section className="border-l-2 border-line py-4 pl-5 text-sm text-muted">Diagnosis will appear here after the investigation completes.</section>
          )}
          <section className="flex flex-col items-start border-t border-line pt-7 sm:flex-row sm:items-center sm:justify-between">
            <div><p className="font-mono text-xs uppercase tracking-[0.16em] text-action">Kubernetes archive</p><h2 className="mt-2 text-2xl font-extrabold tracking-[-0.04em]">Past investigations</h2></div>
            <Link href="/kubernetes/history" className="mt-4 inline-flex min-h-11 items-center gap-2 border border-line px-4 text-sm font-bold text-ink transition hover:border-action hover:text-action sm:mt-0">View Kubernetes history <ArrowLeft size={16} className="rotate-180" /></Link>
          </section>
        </div>
      </div>
    </main>
  );
}
