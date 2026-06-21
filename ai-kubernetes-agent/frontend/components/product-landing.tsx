import { ArrowUpRight, ChartLineUp, CheckCircle, Stack, TerminalWindow } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";

const products = [
  {
    href: "/kubernetes",
    eyebrow: "Cluster operations",
    title: "Kubernetes Troubleshooter",
    description: "Trace failing workloads from symptoms to root cause with live, evidence-backed investigation steps.",
    action: "Troubleshoot Kubernetes",
    icon: Stack,
    features: ["Pod, event, log, and network inspection", "AI root-cause diagnosis", "Reviewable kubectl fixes"],
    accent: "border-action",
    iconStyle: "bg-[#eaf2ff] text-action",
  },
  {
    href: "/cost-analysis",
    eyebrow: "Cloud FinOps",
    title: "Cost Analyzer",
    description: "Scan cloud inventory for waste, pricing mismatches, and configuration choices that quietly increase spend.",
    action: "Analyze Cloud Costs",
    icon: ChartLineUp,
    features: ["Resource-group inventory scans", "Estimated monthly and annual savings", "Reviewable Cloud CLI commands"],
    accent: "border-ready",
    iconStyle: "bg-[#e8f7ef] text-ready",
  },
];

export function ProductLanding() {
  return (
    <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:px-12 lg:py-16">
      <header className="max-w-4xl">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-action">CloudOps operations workspace</p>
        <h1 className="mt-4 text-5xl font-extrabold leading-[1.01] tracking-[-0.06em] sm:text-7xl">What do you need to fix?</h1>
        <p className="mt-6 max-w-2xl text-lg leading-8 text-muted">Choose an operational lens. Investigate Kubernetes failures or find cloud costs worth removing—each workflow keeps its own reports and live progress.</p>
      </header>

      <section className="mt-11 grid gap-5 lg:grid-cols-2" aria-label="Available tools">
        {products.map(({ href, eyebrow, title, description, action, icon: Icon, features, accent, iconStyle }) => (
          <article key={href} className={`group flex min-h-[430px] flex-col border border-line border-t-4 ${accent} bg-white/85 p-6 transition hover:-translate-y-1 hover:shadow-[0_22px_60px_rgba(8,39,84,0.1)] sm:p-8`}>
            <div className="flex items-start justify-between gap-5">
              <span className={`grid size-14 place-items-center ${iconStyle}`}><Icon size={28} weight="bold" /></span>
              <TerminalWindow size={22} className="text-[#aebdd0]" />
            </div>
            <p className="mt-8 font-mono text-[11px] uppercase tracking-[0.16em] text-muted">{eyebrow}</p>
            <h2 className="mt-3 text-3xl font-extrabold tracking-[-0.045em] sm:text-4xl">{title}</h2>
            <p className="mt-4 max-w-xl leading-7 text-muted">{description}</p>
            <ul className="mt-6 space-y-3 text-sm text-ink">
              {features.map((feature) => <li key={feature} className="flex items-center gap-3"><CheckCircle size={18} weight="fill" className="shrink-0 text-ready" />{feature}</li>)}
            </ul>
            <Link href={href} className="mt-auto inline-flex min-h-14 items-center justify-between bg-ink px-5 font-extrabold text-white transition group-hover:bg-action focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-action/30">
              {action}<ArrowUpRight size={20} weight="bold" />
            </Link>
          </article>
        ))}
      </section>
    </div>
  );
}
