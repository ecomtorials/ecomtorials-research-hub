import { NextResponse, type NextRequest } from 'next/server';
import { createSupabaseServerClient } from '@/lib/supabase/server';
import { getClient, insertJob } from '@/lib/db/jobs';
import { triggerWorker } from '@/lib/worker/client';
import type { JobPayload, ResearchMode } from '@research-hub/shared';

interface RequestBody {
  clientId?: string;
  mode?: ResearchMode;
  sourceJobId?: string;
  url?: string;
  brand?: string;
  productName?: string;
  angle?: string;
}

// `custom` is intentionally excluded: it remains in the DB enum (and the worker
// still accepts it for direct API use) but is no longer an offered mode in the
// UI nor valid for new jobs via this route.
const VALID_MODES: ResearchMode[] = ['full', 'angle', 'ump_only'];

export async function POST(request: NextRequest) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user || !user.email?.endsWith('@ecomtorials.de')) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  let body: RequestBody;
  try {
    body = (await request.json()) as RequestBody;
  } catch {
    return NextResponse.json({ error: 'invalid_json' }, { status: 400 });
  }

  const { clientId, mode, url, brand, angle, productName, sourceJobId } = body;

  if (!clientId || !mode || !url || !brand || !angle) {
    return NextResponse.json({ error: 'missing_fields' }, { status: 400 });
  }
  if (mode === 'custom') {
    return NextResponse.json(
      { error: 'custom_mode_deprecated', detail: 'Use full, angle or ump_only.' },
      { status: 400 },
    );
  }
  if (!VALID_MODES.includes(mode)) {
    return NextResponse.json({ error: 'invalid_mode' }, { status: 400 });
  }
  if (mode === 'ump_only' && !sourceJobId) {
    return NextResponse.json({ error: 'ump_only_requires_source_job' }, { status: 400 });
  }

  // Validate client exists
  const client = await getClient(clientId);
  if (!client) {
    return NextResponse.json({ error: 'client_not_found' }, { status: 404 });
  }

  // Insert the job row (service-role bypasses RLS)
  const job = await insertJob({
    clientId,
    userId: user.id,
    mode,
    sourceJobId: mode === 'ump_only' ? sourceJobId : undefined,
    url,
    brand,
    productName,
    angle,
  });

  // Fire-and-forget trigger to the Railway worker. If the worker is down we
  // still return the job id so the user sees it in "queued" state.
  const payload: JobPayload = {
    jobId: job.id,
    clientId: job.client_id,
    mode: job.mode,
    customSteps: job.custom_steps ?? undefined,
    sourceJobId: job.source_job_id ?? undefined,
    url: job.url,
    brand: job.brand,
    productName: job.product_name ?? undefined,
    angle: job.angle,
  };

  try {
    await triggerWorker(payload);
  } catch (err) {
    console.error('[api/jobs] worker trigger failed', err);
    // Worker is unavailable — job stays in "queued". A later retry from the UI
    // will re-trigger it. We don't fail the request because the row exists.
  }

  return NextResponse.json({ jobId: job.id }, { status: 201 });
}
