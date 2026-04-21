import Link from 'next/link';
import { notFound } from 'next/navigation';
import { createSupabaseServerClient } from '@/lib/supabase/server';
import { getJob, getJobSteps, getClient } from '@/lib/db/jobs';
import { listJobActivity } from '@/lib/db/activity';
import { TopBar } from '@/components/TopBar';
import { ModeBadge, StatusBadge } from '@/components/ModeBadge';
import { JobProgress } from './_components/JobProgress';

export default async function JobDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const job = await getJob(id);
  if (!job) return notFound();

  const [steps, client, activity] = await Promise.all([
    getJobSteps(id),
    getClient(job.client_id),
    listJobActivity(id, 100),
  ]);

  return (
    <>
      <TopBar email={user?.email ?? undefined} />
      <main className="mx-auto max-w-4xl px-6 py-10">
        <div className="mb-6">
          <Link
            href="/"
            className="text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
          >
            ← Dashboard
          </Link>
        </div>

        <div className="card mb-6 p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-semibold tracking-tight">
                  {job.brand}
                  {job.product_name ? <span className="text-[var(--color-text-muted)]"> · {job.product_name}</span> : null}
                </h1>
                <ModeBadge mode={job.mode} />
                <StatusBadge status={job.status} />
              </div>
              <p className="mt-1 text-sm text-[var(--color-text-muted)]">
                {client?.name ?? 'Unbekannter Kunde'} · {job.angle}
              </p>
              <p className="mt-2 text-xs text-[var(--color-text-muted)]">
                <a href={job.url} target="_blank" rel="noreferrer" className="underline hover:text-[var(--color-text)]">
                  {job.url}
                </a>
              </p>
            </div>
            <div className="text-right text-sm">
              {job.quality_score != null && (
                <div>
                  <span className="text-[var(--color-text-muted)]">Score </span>
                  <span className="font-mono text-lg">{Number(job.quality_score).toFixed(1)}/10</span>
                </div>
              )}
              <div>
                <span className="text-[var(--color-text-muted)]">Kosten </span>
                <span className="font-mono">${Number(job.cost_usd).toFixed(2)}</span>
              </div>
            </div>
          </div>

          {job.error && (
            <div className="mt-4 rounded-md border border-red-900/50 bg-red-950/40 p-3 text-sm text-red-200">
              <strong>Fehler:</strong> {job.error}
            </div>
          )}

          {(job.status === 'succeeded' || job.status === 'completed_with_warnings') && (
            <div className="mt-4 flex flex-wrap gap-2">
              <Link
                href={`/jobs/${job.id}/result`}
                className="rounded-md bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-zinc-950 hover:brightness-110"
              >
                Report ansehen
              </Link>
              {job.drive_folder_url && (
                <a
                  href={job.drive_folder_url}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-md border border-[var(--color-border)] px-4 py-2 text-sm hover:bg-white/5"
                >
                  In Drive öffnen ↗
                </a>
              )}
            </div>
          )}
        </div>

        <JobProgress
          jobId={job.id}
          initialJob={job}
          initialSteps={steps}
          initialActivity={activity}
        />
      </main>
    </>
  );
}
