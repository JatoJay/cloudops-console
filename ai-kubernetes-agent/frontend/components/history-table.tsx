import type { InvestigationRun } from "@/types/investigation";

export function HistoryTable({ runs, isLoading }: { runs: InvestigationRun[]; isLoading: boolean }) {
  return (
    <section className="border-t border-line pt-7" aria-labelledby="history-title">
      <div className="flex items-end justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-action">History</p>
          <h2 id="history-title" className="mt-2 text-2xl font-extrabold tracking-[-0.04em]">Recent investigations</h2>
        </div>
        <span className="font-mono text-xs text-muted">{runs.length} records</span>
      </div>
      <div className="mt-5 overflow-x-auto">
        <table className="w-full min-w-[680px] border-collapse text-left text-sm">
          <thead className="border-y border-line font-mono text-xs uppercase tracking-[0.1em] text-muted">
            <tr><th className="py-3 pr-5 font-medium">Timestamp</th><th className="py-3 pr-5 font-medium">Root cause</th><th className="py-3 pr-5 font-medium">Namespace</th><th className="py-3 pr-5 font-medium">Confidence</th><th className="py-3 font-medium">Status</th></tr>
          </thead>
          <tbody className="divide-y divide-line">
            {runs.map((run) => (
              <tr key={run.id}>
                <td className="py-4 pr-5 font-mono text-xs text-muted">{new Date(run.created_at).toLocaleString()}</td>
                <td className="max-w-md py-4 pr-5 font-bold text-ink">{run.root_cause ?? "Investigation incomplete"}</td>
                <td className="py-4 pr-5 text-muted">{run.namespace}</td>
                <td className="py-4 pr-5 font-mono text-ink">{run.confidence == null ? "—" : `${run.confidence}%`}</td>
                <td className="py-4"><span className="font-mono text-xs uppercase tracking-[0.08em] text-muted">{run.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
        {!isLoading && runs.length === 0 ? <p className="py-9 text-sm text-muted">No Kubernetes investigations yet. Run the first cluster check from the troubleshooter.</p> : null}
        {isLoading ? <p className="py-9 text-sm text-muted">Loading investigation history…</p> : null}
      </div>
    </section>
  );
}
