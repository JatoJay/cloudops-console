import type { Diagnosis } from "@/types/investigation";

export function DiagnosisCard({ diagnosis }: { diagnosis: Diagnosis }) {
  return (
    <section className="border border-line bg-white/85" aria-labelledby="diagnosis-title">
      <div className="border-b border-line px-6 py-5 sm:px-8">
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-action">Diagnosis</p>
        <h2 id="diagnosis-title" className="mt-2 text-3xl font-extrabold tracking-[-0.045em]">{diagnosis.root_cause}</h2>
      </div>
      <div className="grid gap-8 p-6 sm:p-8 lg:grid-cols-[1.25fr_1fr]">
        <div>
          <h3 className="text-sm font-extrabold uppercase tracking-[0.08em]">Explanation</h3>
          <p className="mt-3 leading-7 text-muted">{diagnosis.explanation}</p>
          <h3 className="mt-7 text-sm font-extrabold uppercase tracking-[0.08em]">Suggested fix</h3>
          <p className="mt-3 leading-7 text-muted">{diagnosis.fix}</p>
        </div>
        <div>
          <div className="border-l-2 border-ready pl-5">
            <span className="font-mono text-xs uppercase tracking-[0.14em] text-muted">Confidence</span>
            <p className="mt-1 text-5xl font-extrabold tracking-[-0.06em] text-ink">{diagnosis.confidence}%</p>
          </div>
          <h3 className="mt-7 text-sm font-extrabold uppercase tracking-[0.08em]">kubectl commands</h3>
          <div className="mt-3 space-y-2">
            {diagnosis.kubectl_commands.map((command) => (
              <code key={command} className="block overflow-x-auto bg-[#f2f6fa] px-4 py-3 font-mono text-xs text-ink">{command}</code>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
