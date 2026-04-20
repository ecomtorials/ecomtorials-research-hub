import Link from 'next/link';
import { notFound } from 'next/navigation';
import { createSupabaseServerClient } from '@/lib/supabase/server';
import { getJob, getClient } from '@/lib/db/jobs';
import { TopBar } from '@/components/TopBar';
import { ModeBadge, StatusBadge } from '@/components/ModeBadge';
import { MarkdownViewer } from './_components/MarkdownViewer';

export default async function ResultPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const job = await getJob(id);
  if (!job) return notFound();

  // Fetch the main MD artifact
  const { data: artifacts } = await supabase
    .schema('research')
    .from('job_artifacts')
    .select('kind, storage_path, drive_url, size_bytes')
    .eq('job_id', id);

  const mdArtifact = artifacts?.find((a) => a.kind === 'md');
  const docxArtifact = artifacts?.find((a) => a.kind === 'docx');

  let markdown = '';
  if (mdArtifact?.storage_path) {
    const { data } = await supabase.storage
      .from('research-reports')
      .download(mdArtifact.storage_path);
    if (data) markdown = await data.text();
  }

  const client = await getClient(job.client_id);

  return (
    <>
      <TopBar email={user?.email ?? undefined} />
      <main className="mx-auto max-w-4xl px-6 py-10">
        <div className="mb-6">
          <Link
            href={`/jobs/${job.id}`}
            className="text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
          >
            ← Job-Details
          </Link>
        </div>

        <div className="card mb-6 p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-semibold tracking-tight">
                  Research: {job.brand}
                </h1>
                <ModeBadge mode={job.mode} />
                <StatusBadge status={job.status} />
              </div>
              <p className="mt-1 text-sm text-[var(--color-text-muted)]">
                {client?.name ?? '—'} · {job.angle}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {markdown && (
                <a
                  href={`/api/jobs/${job.id}/download?format=md`}
                  className="rounded-md bg-[var(--color-accent)] px-3 py-1.5 text-sm font-medium text-zinc-950 hover:brightness-110"
                >
                  MD herunterladen
                </a>
              )}
              {docxArtifact && (
                <a
                  href={`/api/jobs/${job.id}/download?format=docx`}
                  className="rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm hover:bg-white/5"
                >
                  DOCX herunterladen
                </a>
              )}
              {job.drive_folder_url && (
                <a
                  href={job.drive_folder_url}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm hover:bg-white/5"
                >
                  Drive-Ordner ↗
                </a>
              )}
            </div>
          </div>
        </div>

        {markdown ? (
          <MarkdownViewer markdown={markdown} />
        ) : (
          <div className="card p-8 text-center text-sm text-[var(--color-text-muted)]">
            Noch kein Report verfügbar. Entweder läuft der Job noch oder das Artifact wurde nicht hochgeladen.
          </div>
        )}
      </main>
    </>
  );
}
