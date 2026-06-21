"use client";

import { ArrowClockwise, Check, Copy, LinkSimple, ShieldCheck, Trash } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";

type Cluster = { id: string; name: string; status: string; last_seen?: string; created_at: string };
type Pairing = { token: string; expires_at: string; helm_command: string; cli_command: string };
type Job = { id: string; job_type: string; status: string; created_at: string; error?: string };

export function ClusterConnections() {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [name, setName] = useState("");
  const [pairing, setPairing] = useState<Pairing | null>(null);
  const [jobs, setJobs] = useState<Record<string, Job[]>>({});
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState("");

  const refresh = useCallback(async () => {
    const response = await fetch("/api/cluster-agent/remote-clusters", { cache: "no-store" });
    if (response.ok) setClusters(await response.json());
  }, []);
  useEffect(() => {
    const initial = setTimeout(() => void refresh(), 0);
    const interval = setInterval(() => void refresh(), 10_000);
    return () => { clearTimeout(initial); clearInterval(interval); };
  }, [refresh]);

  async function generate() {
    if (!name.trim()) return;
    setBusy(true);
    const response = await fetch("/api/cluster-agent/cluster-connections/pairing-token", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ cluster_name: name.trim() }) });
    if (response.ok) setPairing(await response.json());
    setBusy(false);
  }
  async function run(cluster: Cluster, job_type: "investigate" | "vulnerability_scan") {
    await fetch(`/api/cluster-agent/remote-clusters/${cluster.id}/jobs`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ job_type, payload: {} }) });
    await loadJobs(cluster.id);
  }
  async function loadJobs(id: string) {
    const response = await fetch(`/api/cluster-agent/remote-clusters/${id}/jobs`);
    if (response.ok) {
      const data: Job[] = await response.json();
      setJobs((value) => ({ ...value, [id]: data }));
    }
  }
  async function remove(id: string) {
    if (!confirm("Revoke this cluster agent? Its queued jobs will also be removed.")) return;
    await fetch(`/api/cluster-agent/remote-clusters/${id}`, { method: "DELETE" });
    await refresh();
  }
  async function copy(label: string, value: string) { await navigator.clipboard.writeText(value); setCopied(label); setTimeout(() => setCopied(""), 1500); }

  return <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-12">
    <p className="font-mono text-xs uppercase tracking-[0.18em] text-action">Private cluster connectivity</p>
    <h1 className="mt-4 text-5xl font-extrabold tracking-[-0.055em]">Connect a cluster.</h1>
    <p className="mt-5 max-w-3xl text-lg leading-8 text-muted">Install a read-only agent inside Kubernetes. It connects outbound to CloudOps Console; your API server and kubeconfig stay private.</p>
    <section className="mt-9 grid gap-6 lg:grid-cols-[380px_1fr]">
      <div className="border border-line bg-white p-6">
        <div className="flex items-center gap-3"><ShieldCheck size={25} className="text-ready" weight="fill" /><h2 className="text-xl font-extrabold">Generate pairing token</h2></div>
        <label className="mt-6 block text-sm font-bold" htmlFor="cluster-name">Cluster name</label>
        <input id="cluster-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="production-eu" className="mt-2 h-12 w-full border border-line px-3 outline-none focus:border-action" />
        <button onClick={generate} disabled={busy || !name.trim()} className="mt-4 min-h-12 w-full bg-action px-5 font-bold text-white disabled:opacity-50">{busy ? "Generating…" : "Generate install command"}</button>
        <p className="mt-4 text-xs leading-5 text-muted">Token expires after 15 minutes. The server stores only its SHA-256 hash.</p>
      </div>
      <div className="border border-line bg-[#0c1c33] p-6 text-white">
        <h2 className="font-bold">Helm install</h2>
        {pairing ? <><pre className="mt-4 overflow-x-auto whitespace-pre-wrap break-all font-mono text-xs leading-6 text-[#cce0ff]">{pairing.helm_command}</pre><button onClick={() => copy("helm", pairing.helm_command)} className="mt-4 inline-flex items-center gap-2 border border-white/30 px-4 py-2 text-sm font-bold">{copied === "helm" ? <Check /> : <Copy />} Copy command</button><p className="mt-4 text-xs text-[#9cb2cf]">Expires {new Date(pairing.expires_at).toLocaleString()}</p></> : <p className="mt-4 text-sm text-[#9cb2cf]">Generate a token to reveal the one-time install command.</p>}
      </div>
    </section>
    <section className="mt-10">
      <div className="flex items-center justify-between"><h2 className="text-2xl font-extrabold">Connected clusters</h2><button onClick={refresh} className="inline-flex items-center gap-2 text-sm font-bold text-action"><ArrowClockwise /> Refresh</button></div>
      <div className="mt-5 space-y-4">{clusters.length ? clusters.map((cluster) => <article key={cluster.id} className="border border-line bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-4"><div><div className="flex items-center gap-2"><span className={`size-2 rounded-full ${cluster.status === "online" ? "bg-ready" : "bg-muted"}`} /><h3 className="font-extrabold">{cluster.name}</h3><span className="font-mono text-[10px] uppercase text-muted">{cluster.status}</span></div><p className="mt-1 text-xs text-muted">Last seen {cluster.last_seen ? new Date(cluster.last_seen).toLocaleString() : "never"}</p></div><div className="flex gap-2"><button disabled={cluster.status !== "online"} onClick={() => run(cluster, "investigate")} className="border border-action px-3 py-2 text-sm font-bold text-action disabled:opacity-40">Investigate</button><button disabled={cluster.status !== "online"} onClick={() => run(cluster, "vulnerability_scan")} className="border border-action px-3 py-2 text-sm font-bold text-action disabled:opacity-40">Scan security</button><button aria-label="Revoke agent" onClick={() => remove(cluster.id)} className="px-3 text-red-700"><Trash /></button></div></div>
        <button onClick={() => loadJobs(cluster.id)} className="mt-4 inline-flex items-center gap-2 text-xs font-bold text-muted"><LinkSimple /> Load recent jobs</button>
        {jobs[cluster.id]?.length ? <ul className="mt-3 divide-y divide-line border-t border-line">{jobs[cluster.id].map((job) => <li key={job.id} className="flex justify-between py-3 text-sm"><span>{job.job_type.replace("_", " ")}</span><span className="font-mono text-xs uppercase text-muted">{job.status}</span></li>)}</ul> : null}
      </article>) : <div className="border border-dashed border-line p-8 text-muted">No agents paired yet.</div>}</div>
    </section>
  </div>;
}
