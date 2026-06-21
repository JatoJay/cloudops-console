"use client";

import { useHealth } from "@/hooks/use-health";

export function StatusIndicator() {
  const { data, isError, isPending } = useHealth();
  const isReady = data?.status === "healthy";
  const label = isPending ? "Checking" : isError ? "Unavailable" : isReady ? "Ready" : "Unknown";

  return (
    <div className="flex items-center gap-3 font-mono text-sm tracking-tight text-ink sm:text-base" role="status">
      <span
        aria-hidden="true"
        className={`h-3 w-3 rounded-full ${isReady ? "bg-ready" : isError ? "bg-red-500" : "animate-pulse bg-slate-400"}`}
      />
      <span>
        System Status: <strong className="font-medium">{label}</strong>
      </span>
    </div>
  );
}
