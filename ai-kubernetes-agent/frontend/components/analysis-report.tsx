"use client";

import { ArrowLeft, Check, Clipboard, Coins, TerminalWindow, WarningCircle } from "@phosphor-icons/react";
import Link from "next/link";
import { useState } from "react";

import { useAnalysisHistory } from "@/hooks/use-cost-analysis";
import type { CostIssue, EstimatedSavings, Severity } from "@/types/cost-analysis";

const severityStyle: Record<Severity, string> = {
  high: "border-red-300 bg-red-50 text-red-800",
  medium: "border-amber-300 bg-amber-50 text-amber-800",
  low: "border-green-300 bg-green-50 text-green-800",
};

export function AnalysisReport({ analysisId, userId }: { analysisId: string; userId: string }) {
  const history = useAnalysisHistory(userId);
  const record = history.data?.find((item) => item.id === analysisId);

  if (history.isLoading || (history.isFetching && !record)) return <ReportState title="Loading analysis report…" />;
  if (history.isError) return <ReportState title="The analysis report could not be loaded." />;
  if (!record) return <ReportState title="Analysis report not found." />;

  const analysis = record.analysis_result;
  return (
    <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-12 lg:py-11">
      <Link href="/cost-analysis/history" className="inline-flex items-center gap-2 text-sm font-bold text-muted transition hover:text-action"><ArrowLeft size={17} /> Back to cost history</Link>

      <header className="mt-7 grid gap-7 border-b border-line pb-9 lg:grid-cols-[1fr_320px] lg:items-end">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <span className="font-mono text-xs uppercase tracking-[0.17em] text-action">Analysis report</span>
            <span className="border border-line bg-white px-2 py-1 font-mono text-[10px] uppercase tracking-[0.1em] text-muted">{record.resource_group}</span>
          </div>
          <h1 className="mt-4 max-w-4xl text-4xl font-extrabold leading-tight tracking-[-0.05em] sm:text-6xl">{analysis.summary}</h1>
          <p className="mt-5 font-mono text-xs text-muted">{new Date(record.created_at).toLocaleString()} · {record.resources_scanned} resources scanned</p>
        </div>
        <SavingsLedger savings={analysis.estimated_savings} />
      </header>

      <section className="grid gap-px border-b border-line bg-line sm:grid-cols-3" aria-label="Analysis summary">
        <ReportMetric label="Resources scanned" value={String(record.resources_scanned)} />
        <ReportMetric label="Issues found" value={String(record.issues_found)} />
        <ReportMetric label="Estimated monthly savings" value={money(analysis.estimated_savings.monthly, analysis.estimated_savings.currency)} accent />
      </section>

      <section className="py-10" aria-labelledby="issues-title">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.16em] text-action">Findings</p>
            <h2 id="issues-title" className="mt-2 text-3xl font-extrabold tracking-[-0.045em]">{analysis.issues.length} cost issues</h2>
          </div>
          <p className="max-w-md text-sm leading-6 text-muted">Commands are recommendations. Review account, region, and impact before running them.</p>
        </div>

        <div className="mt-7 space-y-5">
          {analysis.issues.map((issue, index) => <IssueCard key={`${issue.resource_id}-${index}`} issue={issue} index={index} />)}
          {!analysis.issues.length ? <div className="border border-ready/30 bg-[#effaf4] p-7 font-bold text-ready">No cost issues were identified in this scan.</div> : null}
        </div>
      </section>

      {analysis.assumptions.length ? (
        <section className="border-t border-line py-8" aria-labelledby="assumptions-title">
          <h2 id="assumptions-title" className="text-lg font-extrabold">Assumptions and evidence limits</h2>
          <ul className="mt-4 grid gap-2 text-sm leading-6 text-muted sm:grid-cols-2">
            {analysis.assumptions.map((assumption) => <li key={assumption} className="border-l border-line pl-4">{assumption}</li>)}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

function SavingsLedger({ savings }: { savings: EstimatedSavings }) {
  return (
    <aside className="border-t-2 border-ready bg-[#effaf4] p-5">
      <div className="flex items-center justify-between text-ready"><span className="font-mono text-[10px] uppercase tracking-[0.16em]">Savings estimate</span><Coins size={20} weight="fill" /></div>
      <p className="mt-4 text-4xl font-extrabold tracking-[-0.055em] text-ink">{money(savings.monthly, savings.currency)}</p>
      <p className="mt-1 text-sm text-muted">per month</p>
      <div className="mt-4 border-t border-ready/20 pt-3 font-mono text-xs text-muted">{money(savings.annual, savings.currency)} annualized</div>
    </aside>
  );
}

function IssueCard({ issue, index }: { issue: CostIssue; index: number }) {
  return (
    <article className="border border-line bg-white/85">
      <div className="grid border-b border-line lg:grid-cols-[76px_1fr_auto]">
        <div className="grid min-h-16 place-items-center border-b border-line font-mono text-sm text-muted lg:border-b-0 lg:border-r">{String(index + 1).padStart(2, "0")}</div>
        <div className="px-5 py-4 sm:px-6">
          <p className="font-mono text-[10px] uppercase tracking-[0.13em] text-muted">{issueType(issue.category)}</p>
          <h3 className="mt-1 text-xl font-extrabold tracking-[-0.025em]">{issue.resource_name}</h3>
        </div>
        <div className="flex items-center px-5 pb-4 sm:px-6 lg:pb-0">
          <span className={`border px-3 py-1 font-mono text-[10px] font-bold uppercase tracking-[0.13em] ${severityStyle[issue.severity]}`}>{issue.severity}</span>
        </div>
      </div>
      <div className="grid gap-7 p-5 sm:p-6 lg:grid-cols-[1fr_1.1fr]">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.13em] text-muted">Explanation</p>
          <p className="text-base font-bold leading-7 text-ink">{issue.finding}</p>
          <p className="mt-3 text-sm leading-6 text-muted">{issue.rationale}</p>
          <p className="mt-5 font-mono text-xs text-ready">Potential: {money(issue.estimated_savings.monthly, issue.estimated_savings.currency)}/month</p>
        </div>
        <div>
          <div className="flex items-center gap-2"><TerminalWindow size={18} className="text-action" /><h4 className="text-sm font-extrabold">Reviewable fix commands</h4></div>
          <div className="mt-3 space-y-2">
            {issue.fix_commands.map((command) => <CopyCommand key={command} command={command} />)}
            {!issue.fix_commands.length ? <p className="text-sm text-muted">No safe command was generated for this finding.</p> : null}
          </div>
        </div>
      </div>
    </article>
  );
}

function ReportMetric({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="bg-canvas px-5 py-6 sm:px-7">
      <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted">{label}</p>
      <p className={`mt-2 text-3xl font-extrabold tracking-[-0.045em] ${accent ? "text-ready" : "text-ink"}`}>{value}</p>
    </div>
  );
}

function CopyCommand({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    await navigator.clipboard.writeText(command);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1_500);
  }
  return (
    <div className="group flex items-start gap-2 bg-[#f2f6fa] p-3">
      <code className="min-w-0 flex-1 overflow-x-auto whitespace-pre font-mono text-xs leading-6 text-ink">{command}</code>
      <button type="button" onClick={copy} className="grid size-8 shrink-0 place-items-center text-muted hover:bg-white hover:text-action focus-visible:outline focus-visible:outline-2 focus-visible:outline-action" aria-label="Copy command">
        {copied ? <Check size={16} className="text-ready" /> : <Clipboard size={16} />}
      </button>
    </div>
  );
}

function ReportState({ title }: { title: string }) {
  return <div className="mx-auto flex min-h-[60vh] max-w-7xl items-center gap-3 px-5 text-lg font-bold text-muted sm:px-8 lg:px-12"><WarningCircle size={22} />{title}</div>;
}

function money(value: number, currency: string) {
  return new Intl.NumberFormat(undefined, { style: "currency", currency, maximumFractionDigits: 0 }).format(value);
}

function issueType(category: CostIssue["category"]) {
  return {
    over_provisioning: "Over-provisioned",
    unused_or_idle: "Unused",
    misconfiguration: "Misconfigured",
    wrong_pricing_tier: "Wrong pricing tier",
    cost_optimization: "Cost optimization",
  }[category];
}
