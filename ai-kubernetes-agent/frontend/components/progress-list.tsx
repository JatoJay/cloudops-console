import { CheckCircle, Circle, SpinnerGap, WarningCircle } from "@phosphor-icons/react/dist/ssr";

import type { InvestigationStep } from "@/types/investigation";

const steps: Array<{ id: InvestigationStep; label: string }> = [
  { id: "checking_pods", label: "Checking Pods" },
  { id: "reading_logs", label: "Reading Logs" },
  { id: "analyzing_events", label: "Analyzing Events" },
  { id: "inspecting_deployments", label: "Inspecting Deployments" },
  { id: "checking_networking", label: "Checking Networking" },
  { id: "ai_reasoning", label: "AI Reasoning" },
  { id: "root_cause_found", label: "Root Cause Found" },
];

export function ProgressList({ currentStep, isRunning, clusterHealthy = false }: { currentStep: InvestigationStep; isRunning: boolean; clusterHealthy?: boolean }) {
  const currentIndex = steps.findIndex((step) => step.id === currentStep);

  return (
    <ol className="mt-6 grid gap-1" aria-label="Investigation progress">
      {steps.map((step, index) => {
        const complete = currentStep === "root_cause_found" || index < currentIndex;
        const active = isRunning && index === currentIndex;
        const failed = currentStep === "failed" && index === Math.max(currentIndex, 0);
        return (
          <li key={step.id} className={`flex min-h-11 items-center gap-3 border-l px-4 text-sm ${active ? "border-action bg-[#eef5ff] font-bold text-ink" : "border-line text-muted"}`}>
            {complete ? <CheckCircle size={19} weight="fill" className="text-ready" /> : active ? <SpinnerGap size={19} className="animate-spin text-action" /> : failed ? <WarningCircle size={19} weight="fill" className="text-red-600" /> : <Circle size={19} className="text-[#aebdd0]" />}
            <span>{step.id === "root_cause_found" && clusterHealthy ? "Cluster Check Complete" : step.label}</span>
          </li>
        );
      })}
    </ol>
  );
}
