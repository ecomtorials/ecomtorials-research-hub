import Link from 'next/link';
import { redirect } from 'next/navigation';
import { createSupabaseServerClient } from '@/lib/supabase/server';
import { listJobs, listClients } from '@/lib/db/jobs';
import { TopBar } from '@/components/TopBar';
import { ModeBadge, StatusBadge } from '@/components/ModeBadge';

function formatRelative(iso: string): string {
  const d = new Date(iso);
  const mins = Math.round((Date.now() - d.getTime()) / 60000);
  if (mins < 1) return 'gerade eben';
  if (mins < 60) return `vor ${mins} min`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `vor ${hours} h`;
  const days = Math.round(hours / 24);
  return `vor ${days} d`;
}

function formatCost(cost: number): string {
  return cost > 0 ? `$${cost.toFixed(2)}` : '—';
}

export default async function DashboardPage() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect('/login');

  const [jobs, clients] = await Promise.all([listJobs(50), listClients()]);
  const clientsById = new Map(clients.map((c) => [c.id, c]));

  return (
    <>
      <TopBar email={user?.email ?? undefined} />
      <main className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8 flex items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Research-Jobs</h1>
            <p className="mt-1 text-sm text-[var(--color-text-muted)]">
              {jobs.length} Job{jobs.length === 1 ? '' : 's'} · {clients.length} Kunden
            </p>
          </div>
          <Link
            href="/new"
            className="rounded-md bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-zinc-950 transition hover:brightness-110"
          >
            + Neue Research
          </Link>
        </div>

        {jobs.length === 0 ? (
          <div className="card p-12 text-center">
            <p className="text-sm text-[var(--color-text-muted)]">
              Noch keine Jobs. Klick „Neue Research" um zu starten.
            </p>
          </div>
        ) : (
          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead className="border-b border-[var(--color-border)] text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                <tr>
                  <th className="px-4 py-3 text-left">Kunde</th>
                  <th className="px-4 py-3 text-left">Brand / Angle</th>
                  <th className="px-4 py-3 text-left">Modus</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-right">Score</th>
                  <th className="px-4 py-3 text-right">Kosten</th>
                  <th className="px-4 py-3 text-right">Erstellt</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => {
                  const client = clientsById.get(job.client_id);
                  return (
                    <tr
                      key={job.id}
                      className="border-b border-[var(--color-border)] last:border-0 hover:bg-white/[0.02]"
                    >
                      <td className="px-4 py-3">
                        <Link href={`/jobs/${job.id}`} className="font-medium hover:text-[var(--color-accent)]">
                          {client?.name ?? <span className="text-[var(--color-text-muted)]">Kunde gelöscht</span>}
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-medium">{job.brand}</div>
                        <div className="text-xs text-[var(--color-text-muted)] line-clamp-1">
                          {job.angle}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <ModeBadge mode={job.mode} />
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={job.status} />
                      </td>
                      <td className="px-4 py-3 text-right">
                        {job.quality_score != null ? (
                          <span className="font-mono">{job.quality_score.toFixed(1)}/10</span>
                        ) : (
                          <span className="text-[var(--color-text-muted)]">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right font-mono">{formatCost(Number(job.cost_usd))}</td>
                      <td className="px-4 py-3 text-right text-[var(--color-text-muted)]">
                        {formatRelative(job.created_at)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </>
  );
}
