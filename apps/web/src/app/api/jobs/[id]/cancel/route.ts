import { NextResponse, type NextRequest } from 'next/server';
import {
  createSupabaseServerClient,
  createSupabaseServiceRoleClient,
} from '@/lib/supabase/server';
import { getJob } from '@/lib/db/jobs';
import { cancelWorkerJob } from '@/lib/worker/client';

/**
 * POST /api/jobs/[id]/cancel
 *
 * Flip a job to status='cancelled' in the DB and best-effort-notify the
 * worker to stop at the next pipeline step boundary. The DB write happens
 * first — even if the worker is unreachable, the UI reflects the intent
 * and the worker's next checkpoint (if it is running) will see the flag
 * via its own memory when/if a cancel call lands.
 */
export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;

  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user || !user.email?.endsWith('@ecomtorials.de')) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  const job = await getJob(id);
  if (!job) return NextResponse.json({ error: 'not_found' }, { status: 404 });

  if (!['queued', 'running'].includes(job.status)) {
    return NextResponse.json(
      { error: 'not_cancelable', status: job.status },
      { status: 409 },
    );
  }

  const service = createSupabaseServiceRoleClient();
  const { error: updateErr } = await service
    .schema('research')
    .from('jobs')
    .update({
      status: 'cancelled',
      finished_at: new Date().toISOString(),
      error: 'cancelled by user',
    })
    .eq('id', id);
  if (updateErr) {
    return NextResponse.json(
      { error: 'db_update_failed', detail: updateErr.message },
      { status: 500 },
    );
  }

  // Activity row so the live log shows the cancel event.
  await service
    .schema('research')
    .from('job_activity')
    .insert({
      job_id: id,
      agent: 'step0',
      kind: 'note',
      detail: `cancelled by ${user.email}`,
    })
    .throwOnError();

  let workerNotified = true;
  let workerError: string | null = null;
  try {
    await cancelWorkerJob(id);
  } catch (e) {
    workerNotified = false;
    workerError = e instanceof Error ? e.message : 'unknown';
  }

  return NextResponse.json({
    ok: true,
    jobId: id,
    workerNotified,
    workerError,
  });
}
