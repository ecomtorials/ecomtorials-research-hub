import { NextResponse, type NextRequest } from 'next/server';
import { createSupabaseServerClient } from '@/lib/supabase/server';
import { getJob, insertJob } from '@/lib/db/jobs';
import { triggerWorker } from '@/lib/worker/client';
import type { JobPayload, ResearchMode } from '@research-hub/shared';

const RETRYABLE_MODES: ResearchMode[] = ['full', 'angle', 'ump_only'];

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

  const original = await getJob(id);
  if (!original) {
    return NextResponse.json({ error: 'job_not_found' }, { status: 404 });
  }
  if (!RETRYABLE_MODES.includes(original.mode)) {
    return NextResponse.json(
      { error: 'mode_not_retryable', detail: `Cannot retry mode "${original.mode}".` },
      { status: 400 },
    );
  }

  const job = await insertJob({
    clientId: original.client_id,
    userId: user.id,
    mode: original.mode,
    sourceJobId: original.source_job_id ?? undefined,
    url: original.url,
    brand: original.brand,
    productName: original.product_name ?? undefined,
    angle: original.angle,
  });

  const payload: JobPayload = {
    jobId: job.id,
    clientId: job.client_id,
    mode: job.mode,
    sourceJobId: job.source_job_id ?? undefined,
    url: job.url,
    brand: job.brand,
    productName: job.product_name ?? undefined,
    angle: job.angle,
  };

  try {
    await triggerWorker(payload);
  } catch (err) {
    console.error('[api/jobs/retry] worker trigger failed', err);
  }

  return NextResponse.json({ jobId: job.id }, { status: 201 });
}
