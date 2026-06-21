import { CheckCircle, Circle, SpinnerGap } from "@phosphor-icons/react";

const steps = [
  { match: "Fetching resource groups...", label: "Fetching resource groups" },
  { match: "Scanning resources", label: "Scanning cloud resources" },
  { match: "Analyzing costs with AI...", label: "Analyzing costs with AI" },
  { match: "Storing results...", label: "Storing results" },
  { match: "Analysis complete", label: "Analysis complete" },
];

export function CostProgress({ progress, isRunning }: { progress: string[]; isRunning: boolean }) {
  const currentIndex = Math.max(0, progress.length ? steps.findIndex((step) => progress.at(-1)?.startsWith(step.match)) : 0);
  const finished = progress.at(-1) === "Analysis complete";

  return (
    <ol className="mt-6 space-y-1" aria-label="Cost analysis progress" aria-live="polite">
      {steps.map((step, index) => {
        const done = finished || index < currentIndex;
        const active = isRunning && !finished && index === currentIndex;
        return (
          <li
            key={step.match}
            className={`flex min-h-12 items-center gap-3 border-l px-4 text-sm transition ${active ? "border-action bg-[#eef5ff] font-bold text-ink" : "border-line text-muted"}`}
          >
            {done ? <CheckCircle size={19} weight="fill" className="text-ready" /> : active ? <SpinnerGap size={19} className="animate-spin text-action" /> : <Circle size={19} className="text-[#aebdd0]" />}
            <span>{step.label}</span>
          </li>
        );
      })}
    </ol>
  );
}
