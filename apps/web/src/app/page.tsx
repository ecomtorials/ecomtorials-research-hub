import Link from 'next/link';
import { redirect } from 'next/navigation';
import { ChevronLeft, ChevronRight, Plus, FileText } from 'lucide-react';
import { createSupabaseServerClient } from '@/lib/supabase/server';
import { listJobsPaged, listClients, type ListJobsFilters } from '@/lib/db/jobs';
import type { JobStatus, ResearchMode } from '@research-hub/shared';
import { TopBar } from '@/components/TopBar';
import { ModeBadge, StatusBadge } from '@/components/ModeBadge';
import { DashboardFilters } from '@/components/DashboardFilters';
import { RetryButton } from '@/components/RetryButton';

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

function formatDuration(startedAt: string | null, finishedAt: string | null): string {
  if (!startedAt) return '—';
  const end = finishedAt ? new Date(finishedAt) : new Date();
  const start = new Date(startedAt);
  const secs = Math.max(0, Math.round((end.getTime() - start.getTime()) / 1000));
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  const rem = secs % 60;
  if (mins < 60) return `${mins}m ${rem}s`;
  const hours = Math.floor(mins / 60);
  return `${hours}h ${mins % 60}m`;
}

function formatCost(cost: number): string {
  return cost > 0 ? `$${cost.toFixed(2)}` : '—';
}

const ALLOWED_STATUSES: JobStatus[] = [
  'queued',
  'running',
  'succeeded',
  'failed',
  'cancelled',
  'completed_with_warnings',
];
const ALLOWED_MODES: ResearchMode[] = ['full', 'angle', 'ump_only', 'custom'];

function parseStatus(raw: string | undefined): JobStatus | 'all' {
  if (!raw || raw === 'all') return 'all';
  return (ALLOWED_STATUSES as string[]).includes(raw) ? (raw as JobStatus) : 'all';
}
function parseMode(raw: string | undefined): ResearchMode | 'all' {
  if (!raw || raw === 'all') return 'all';
  return (ALLOWED_MODES as string[]).includes(raw) ? (raw as ResearchMode) : 'all';
}

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  const sp = await searchParams;
  const first = (v: string | string[] | undefined): string | undefined =>
    Array.isArray(v) ? v[0] : v;

  const status = parseStatus(first(sp.status));
  const mode = parseMode(first(sp.mode));
  const clientId = first(sp.client) ?? 'all';
  const search = first(sp.q) ?? '';
  const sizeRaw = Number(first(sp.size) ?? '25');
  const pageSize = [25, 50, 100].includes(sizeRaw) ? sizeRaw : 25;
  const page = Math.max(1, Number(first(sp.page) ?? '1') || 1);

  const filters: ListJobsFilters = {
    status,
    mode,
    clientId,
    search,
    limit: pageSize,
    offset: (page - 1) * pageSize,
  };

  const [{ rows: jobs, total }, clients] = await Promise.all([
    listJobsPaged(filters),
    listClients(),
  ]);
  const clientsById = new Map(clients.map((c) => [c.id, c]));
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const qs = (p: Record<string, string | number | null>) => {
    const u = new URLSearchParams();
    const base: Record<string, string> = {
      ...(status !== 'all' ? { status } : {}),
      ...(mode !== 'all' ? { mode } : {}),
      ...(clientId !== 'all' ? { client: clientId } : {}),
      ...(search ? { q: search } : {}),
      ...(pageSize !== 25 ? { size: String(pageSize) } : {}),
    };
    for (const [k, v] of Object.entries(base)) u.set(k, v);
    for (const [k, v] of Object.entries(p)) {
      if (v === null || v === '') u.delete(k);
      else u.set(k, String(v));
    }
    return `/?${u.toString()}`;
  };

  const hasAnyFilter =
    status !== 'all' || mode !== 'all' || clientId !== 'all' || search !== '';

  return (
    <>
      <TopBar email={user?.email ?? undefined} />
      <main className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Research-Jobs</h1>
            <p className="mt-1 text-sm text-[var(--color-text-muted)]">
              {total} Job{total === 1 ? '' : 's'} · {clients.length} Kunden
            </p>
          </div>
          <Link href="/new" className="btn-primary inline-flex items-center gap-1.5">
            <Plus className="h-4 w-4" />
            Neue Research
          </Link>
        </div>

        <div className="mb-6">
          <DashboardFilters
            clients={clients}
            currentStatus={status}
            currentMode={mode}
            currentClient={clientId}
            currentSearch={search}
            currentPageSize={pageSize}
          />
        </div>

        {jobs.length === 0 ? (
          <div className="card flex flex-col items-center gap-3 p-16 text-center">
            <FileText className="h-10 w-10 text-[var(--color-text-subtle)]" />
            <p className="text-sm text-[var(--color-text-muted)]">
              {hasAnyFilter
                ? 'Keine Jobs entsprechen den aktuellen Filtern.'
                : 'Noch keine Jobs. Klick „Neue Research" um zu starten.'}
            </p>
          </div>
        ) : (
          <div className="card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-[var(--color-border)] text-xs uppercase tracking-wider text-[var(--color-text-subtle)]">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium">Kunde</th>
                    <th className="px-4 py-3 text-left font-medium">Brand / Angle</th>
                    <th className="px-4 py-3 text-left font-medium">Modus</th>
                    <th className="px-4 py-3 text-left font-medium">Status</th>
                    <th className="px-4 py-3 text-right font-medium">Score</th>
                    <th className="px-4 py-3 text-right font-medium">Kosten</th>
                    <th className="px-4 py-3 text-right font-medium">Dauer</th>
                    <th className="px-4 py-3 text-right font-medium">Erstellt</th>
                    <th className="px-4 py-3 text-right font-medium"></th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((job) => {
                    const client = clientsById.get(job.client_id);
                    const isFailed = job.status === 'failed' || job.status === 'cancelled';
                    return (
                      <tr
                        key={job.id}
                        className="border-b border-[var(--color-border)] last:border-0 transition-colors hover:bg-white/[0.02]"
                      >
                        <td className="px-4 py-3">
                          <Link
                            href={`/jobs/${job.id}`}
                            className="font-medium transition-colors hover:text-[var(--color-accent)]"
                          >
                            {client?.name ?? (
                              <span className="text-[var(--color-text-muted)]">Kunde gelöscht</span>
                            )}
                          </Link>
                        </td>
                        <td className="px-4 py-3">
                          <Link href={`/jobs/${job.id}`} className="block">
                            <div className="font-medium">{job.brand}</div>
                            <div className="line-clamp-1 text-xs text-[var(--color-text-muted)]">
                              {job.angle}
                            </div>
                          </Link>
                        </td>
                        <td className="px-4 py-3">
                          <ModeBadge mode={job.mode} />
                        </td>
                        <td className="px-4 py-3">
                          <StatusBadge status={job.status} />
                        </td>
                        <td className="px-4 py-3 text-right">
                          {job.quality_score != null ? (
                            <span className="font-mono">{Number(job.quality_score).toFixed(1)}</span>
                          ) : (
                            <span className="text-[var(--color-text-subtle)]">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right font-mono">
                          {formatCost(Number(job.cost_usd))}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-[var(--color-text-muted)]">
                          {formatDuration(job.started_at, job.finished_at)}
                        </td>
                        <td className="px-4 py-3 text-right text-[var(--color-text-muted)]">
                          {formatRelative(job.created_at)}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {isFailed && <RetryButton jobId={job.id} />}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-[var(--color-border)] px-4 py-3 text-xs text-[var(--color-text-muted)]">
                <span>
                  Seite {page} von {totalPages} · {total} Jobs
                </span>
                <div className="flex items-center gap-1">
                  {page > 1 ? (
                    <Link
                      href={qs({ page: page - 1 })}
                      className="inline-flex items-center gap-1 rounded-md border border-[var(--color-border)] px-2 py-1 hover:bg-white/5"
                    >
                      <ChevronLeft className="h-3 w-3" /> Zurück
                    </Link>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded-md border border-[var(--color-border)] px-2 py-1 opacity-40">
                      <ChevronLeft className="h-3 w-3" /> Zurück
                    </span>
                  )}
                  {page < totalPages ? (
                    <Link
                      href={qs({ page: page + 1 })}
                      className="inline-flex items-center gap-1 rounded-md border border-[var(--color-border)] px-2 py-1 hover:bg-white/5"
                    >
                      Weiter <ChevronRight className="h-3 w-3" />
                    </Link>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded-md border border-[var(--color-border)] px-2 py-1 opacity-40">
                      Weiter <ChevronRight className="h-3 w-3" />
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </>
  );
}
