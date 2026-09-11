import type { Metadata } from "next";
import Link from "next/link";
import { incidents, scheduledMaintenance, type IncidentState } from "@/content/incidents";
import { maintenancePolicy, sloTargets } from "@/content/slo";
import { api, attempt } from "@/lib/api";
import { brand } from "@/lib/brand";
import { formatDateTime } from "@/lib/format";
import { OVERALL_LABELS, STATE_LABELS, formatMs, parseStatus, type ComponentState, type StatusView } from "@/lib/status";

export const revalidate = 60;

export const metadata: Metadata = {
  title: "Status",
  description: `Live health of ${brand.productName}: components, morph success and latency over the last 24 hours, incidents and scheduled maintenance.`,
};

const STATE_STYLES: Record<ComponentState, string> = {
  operational: "text-success",
  degraded: "text-accent",
  down: "text-danger",
  maintenance: "text-accent",
  unknown: "text-ink-dim",
};

const INCIDENT_STATE_LABELS: Record<IncidentState, string> = {
  investigating: "Investigating",
  identified: "Identified",
  monitoring: "Monitoring",
  resolved: "Resolved",
};

export default async function StatusPage() {
  const result = brand.apiUrl ? await attempt(() => api.getStatus()) : null;
  const view: StatusView | null = result?.ok ? parseStatus(result.data) : null;
  const checkedAt = new Date().toISOString();

  return (
    <div className="container-page py-16 sm:py-24">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Status</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">{view ? OVERALL_LABELS[view.overall] : "Live status unavailable"}</h1>
          <p className="mt-3 text-sm text-ink-muted">
            Checked {formatDateTime(checkedAt)} · refreshed every minute ·{" "}
            <a href="#slo" className="text-ink underline underline-offset-4">
              SLO targets
            </a>
          </p>
        </div>
        {view && (
          <span className={`rounded-full border border-line px-3 py-1 text-sm ${STATE_STYLES[view.overall]}`}>{STATE_LABELS[view.overall]}</span>
        )}
      </div>

      {!view && (
        <p className="alert alert-info mt-8">
          The status API could not be reached from this page, so component health and the last 24 hours are not shown. If
          you can read this, the website itself is up. Morphs may well be working: try one, and remember that a failed morph
          is never charged.
        </p>
      )}

      <div className="mt-10 grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <section className="card" aria-labelledby="components">
          <h2 id="components" className="text-lg font-semibold">
            Components
          </h2>
          <table className="mt-4 w-full text-sm">
            <tbody className="divide-y divide-line">
              {(view?.components ?? parseStatus(null).components).map((component) => (
                <tr key={component.key}>
                  <th scope="row" className="py-3 pr-4 text-left font-medium">
                    {component.label}
                  </th>
                  <td className={`py-3 text-right ${STATE_STYLES[component.state]}`}>
                    {component.raw ?? (view ? STATE_LABELS[component.state] : "—")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="card" aria-labelledby="last24h">
          <h2 id="last24h" className="text-lg font-semibold">
            Last 24 hours
          </h2>
          <dl className="mt-4 grid grid-cols-2 gap-5">
            <Stat label="Morphs" value={view?.last24h.morphs === null || !view ? "—" : view.last24h.morphs.toLocaleString("en-US")} />
            <Stat label="Succeeded" value={view?.last24h.successRatePercent == null ? "—" : `${view.last24h.successRatePercent} %`} />
            <Stat label="Time to result, p50" value={formatMs(view?.last24h.p50Ms ?? null)} />
            <Stat label="Time to result, p95" value={formatMs(view?.last24h.p95Ms ?? null)} />
          </dl>
        </section>
      </div>

      <div className="card mt-6 border-accent/40">
        <p className="text-lg font-medium">A failed morph is never charged — the credit comes back automatically.</p>
        <p className="mt-1 text-sm text-ink-muted">
          Morphs are reserved when they start and captured only on success. If something breaks on our side, the reservation
          is released within minutes and your balance in the plugin updates itself.
        </p>
      </div>

      <section className="mt-12" aria-labelledby="incidents">
        <h2 id="incidents" className="text-2xl font-semibold tracking-tight">
          Incidents
        </h2>
        {incidents.length === 0 ? (
          <p className="mt-3 text-sm text-ink-muted">No incidents in the last 90 days.</p>
        ) : (
          <ol className="mt-6 space-y-8">
            {incidents.map((incident) => (
              <li key={incident.id} className="border-t border-line pt-5">
                <h3 className="font-semibold">{incident.title}</h3>
                <p className="mt-1 text-xs text-ink-dim">Affected: {incident.components.join(", ")}</p>
                <ol className="mt-3 space-y-2 text-sm">
                  {incident.updates.map((update) => (
                    <li key={update.at} className="grid gap-1 sm:grid-cols-[11rem_7rem_1fr]">
                      <span className="text-ink-dim">{formatDateTime(update.at)}</span>
                      <span className="font-medium">{INCIDENT_STATE_LABELS[update.state]}</span>
                      <span className="text-ink-muted">{update.body}</span>
                    </li>
                  ))}
                </ol>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="mt-12" aria-labelledby="maintenance">
        <h2 id="maintenance" className="text-2xl font-semibold tracking-tight">
          Scheduled maintenance
        </h2>
        <p className="mt-3 text-sm text-ink-muted">
          Maintenance is announced here at least {maintenancePolicy.noticeHours} hours ahead and limited to{" "}
          {maintenancePolicy.maxHoursPerMonth} hours a month. While morphing is paused, the plugin shows a banner and nothing
          is charged.
        </p>
        {scheduledMaintenance.length === 0 ? (
          <p className="mt-3 text-sm text-ink-muted">Nothing scheduled.</p>
        ) : (
          <ul className="mt-6 space-y-4">
            {scheduledMaintenance.map((window) => (
              <li key={window.id} className="border-t border-line pt-4 text-sm">
                <p className="font-semibold">{window.title}</p>
                <p className="mt-1 text-ink-dim">
                  {formatDateTime(window.starts_at)} – {formatDateTime(window.ends_at)}
                </p>
                <p className="mt-2 text-ink-muted">{window.body}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section id="slo" className="mt-12 scroll-mt-24" aria-labelledby="slo-title">
        <h2 id="slo-title" className="text-2xl font-semibold tracking-tight">
          SLO targets
        </h2>
        <p className="mt-3 max-w-2xl text-sm text-ink-muted">
          What this page reports against. These are published commitments we revise as the numbers come in, not terms of
          the{" "}
          <Link href="/legal/terms" className="text-ink underline underline-offset-4">
            Terms of Service
          </Link>
          , which promise only what the code guarantees.
        </p>
        <div className="mt-6 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-ink-dim uppercase">
              <tr>
                <th className="py-2 pr-4 font-medium">Objective</th>
                <th className="py-2 pr-4 font-medium">Target</th>
                <th className="py-2 font-medium">How it is measured</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {sloTargets.map((slo) => (
                <tr key={slo.id}>
                  <td className="py-3 pr-4 font-medium">{slo.name}</td>
                  <td className="py-3 pr-4 whitespace-nowrap">{slo.target}</td>
                  <td className="py-3 text-ink-muted">{slo.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-ink-dim uppercase">{label}</dt>
      <dd className="mt-1 text-3xl font-semibold tracking-tight">{value}</dd>
    </div>
  );
}
