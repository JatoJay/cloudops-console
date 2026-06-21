"use client";

import { ArrowClockwise, Check, Copy, GoogleLogo, ShieldCheck, Trash } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";

type Connection = {
  id: string;
  name: string;
  provider: string;
  status: string;
  last_seen?: string;
  metadata: { projects?: Array<{ project_id: string; display_name: string }> };
};
type Pairing = { token: string; expires_at: string; cli_command: string };

export function CloudConnections() {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [name, setName] = useState("Google Cloud");
  const [pairing, setPairing] = useState<Pairing | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  const refresh = useCallback(async () => {
    const response = await fetch("/api/cluster-agent/cloud-connections", { cache: "no-store" });
    if (response.ok) setConnections((await response.json()).connections);
  }, []);
  useEffect(() => {
    const initial = setTimeout(() => void refresh(), 0);
    const interval = setInterval(() => void refresh(), 10_000);
    return () => { clearTimeout(initial); clearInterval(interval); };
  }, [refresh]);

  async function generate() {
    setBusy(true);
    const response = await fetch("/api/cluster-agent/cluster-connections/pairing-token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cluster_name: name.trim(), provider: "gcp" }),
    });
    if (response.ok) setPairing(await response.json());
    setBusy(false);
  }
  async function remove(id: string) {
    if (!confirm("Revoke this Google Cloud connector?")) return;
    await fetch(`/api/cluster-agent/remote-clusters/${id}`, { method: "DELETE" });
    await refresh();
  }
  async function copyCommand() {
    if (!pairing) return;
    await navigator.clipboard.writeText(pairing.cli_command);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-12">
    <p className="font-mono text-xs uppercase tracking-[0.18em] text-action">Keyless cloud access</p>
    <h1 className="mt-4 text-5xl font-extrabold tracking-[-0.055em]">Connect Google Cloud.</h1>
    <p className="mt-5 max-w-3xl text-lg leading-8 text-muted">Run the connector beside your existing gcloud session. CloudOps receives resource inventory only—OAuth tokens, service-account keys, and application-default credentials stay on your machine.</p>

    <section className="mt-9 grid gap-6 lg:grid-cols-[390px_1fr]">
      <div className="border border-line bg-white p-6">
        <div className="flex items-center gap-3"><GoogleLogo size={25} weight="bold" className="text-action" /><h2 className="text-xl font-extrabold">Create connection</h2></div>
        <label className="mt-6 block text-sm font-bold" htmlFor="connection-name">Connection name</label>
        <input id="connection-name" value={name} onChange={(event) => setName(event.target.value)} className="mt-2 h-12 w-full border border-line px-3 outline-none focus:border-action" />
        <button onClick={generate} disabled={busy || !name.trim()} className="mt-4 min-h-12 w-full bg-action px-5 font-bold text-white disabled:opacity-50">{busy ? "Generating…" : "Generate pairing command"}</button>
        <p className="mt-4 text-xs leading-5 text-muted">The one-time token expires in 15 minutes and is stored by CloudOps as a SHA-256 hash.</p>
      </div>
      <div className="border border-line bg-[#0c1c33] p-6 text-white">
        <h2 className="font-bold">Run in Cloud Shell or your terminal</h2>
        <ol className="mt-4 list-decimal space-y-2 pl-5 text-sm text-[#b9cae1]"><li>Install and authenticate the Google Cloud CLI.</li><li>Grant Cloud Asset Viewer and Service Usage Consumer on the projects to scan.</li><li>Run the generated command and keep it running during analysis.</li></ol>
        {pairing ? <><pre className="mt-5 max-h-60 overflow-auto whitespace-pre-wrap break-all border border-white/15 bg-black/20 p-4 font-mono text-xs leading-6 text-[#cce0ff]">{pairing.cli_command}</pre><button onClick={copyCommand} className="mt-4 inline-flex items-center gap-2 border border-white/30 px-4 py-2 text-sm font-bold">{copied ? <Check /> : <Copy />} Copy command</button><p className="mt-3 text-xs text-[#9cb2cf]">Expires {new Date(pairing.expires_at).toLocaleString()}</p></> : <p className="mt-5 text-sm text-[#9cb2cf]">Generate a pairing token to reveal the command.</p>}
      </div>
    </section>

    <section className="mt-10">
      <div className="flex items-center justify-between"><h2 className="text-2xl font-extrabold">Cloud connections</h2><button onClick={refresh} className="inline-flex items-center gap-2 text-sm font-bold text-action"><ArrowClockwise /> Refresh</button></div>
      <div className="mt-5 space-y-4">{connections.length ? connections.map((connection) => <article key={connection.id} className="border border-line bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-4"><div><div className="flex items-center gap-2"><span className={`size-2 rounded-full ${connection.status === "online" ? "bg-ready" : "bg-muted"}`} /><h3 className="font-extrabold">{connection.name}</h3><span className="font-mono text-[10px] uppercase text-muted">{connection.status}</span></div><p className="mt-2 text-sm text-muted">{connection.metadata.projects?.length ?? 0} projects available</p></div><button aria-label="Revoke connector" onClick={() => remove(connection.id)} className="px-3 text-red-700"><Trash /></button></div>
        {connection.metadata.projects?.length ? <ul className="mt-4 grid gap-2 border-t border-line pt-4 sm:grid-cols-2">{connection.metadata.projects.map((project) => <li key={project.project_id} className="flex items-center gap-2 text-sm"><ShieldCheck className="text-ready" />{project.display_name} <span className="text-xs text-muted">{project.project_id}</span></li>)}</ul> : null}
      </article>) : <div className="border border-dashed border-line p-8 text-muted">No Google Cloud connectors paired yet.</div>}</div>
    </section>
  </div>;
}
