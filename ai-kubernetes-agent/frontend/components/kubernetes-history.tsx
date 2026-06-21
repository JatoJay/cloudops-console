"use client";

import { ArrowLeft } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { HistoryTable } from "@/components/history-table";
import { getRecentInvestigations } from "@/services/investigations";

export function KubernetesHistory({ userId }: { userId: string }) {
  const history = useQuery({
    queryKey: ["investigation-history", userId],
    queryFn: getRecentInvestigations,
  });

  return (
    <div className="mx-auto max-w-7xl px-5 py-9 sm:px-8 lg:px-12 lg:py-12">
      <Link href="/kubernetes" className="inline-flex items-center gap-2 text-sm font-bold text-muted transition hover:text-action"><ArrowLeft size={17} /> Back to Kubernetes Troubleshooter</Link>
      <header className="mt-7 border-b border-line pb-8">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-action">Kubernetes archive</p>
        <h1 className="mt-3 text-5xl font-extrabold tracking-[-0.055em] sm:text-6xl">Past investigations.</h1>
        <p className="mt-4 max-w-xl text-lg leading-8 text-muted">Review cluster diagnoses, confidence levels, namespaces, and incomplete troubleshooting runs separately from cloud cost analyses.</p>
      </header>
      <div className="pt-8">
        <HistoryTable runs={history.data ?? []} isLoading={history.isLoading} />
        {history.isError ? <p className="py-6 text-sm text-red-700">Kubernetes investigation history could not be loaded.</p> : null}
      </div>
    </div>
  );
}
