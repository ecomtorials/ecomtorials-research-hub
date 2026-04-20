import { NextResponse, type NextRequest } from 'next/server';
import { createSupabaseServerClient } from '@/lib/supabase/server';
import { getJob } from '@/lib/db/jobs';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const { searchParams } = new URL(request.url);
  const format = (searchParams.get('format') ?? 'md').toLowerCase();

  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user || !user.email?.endsWith('@ecomtorials.de')) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  const job = await getJob(id);
  if (!job) return NextResponse.json({ error: 'not_found' }, { status: 404 });

  const artifactKind = format === 'docx' ? 'docx' : 'md';
  const { data: artifacts } = await supabase
    .schema('research')
    .from('job_artifacts')
    .select('kind, storage_path')
    .eq('job_id', id)
    .eq('kind', artifactKind);

  const artifact = artifacts?.[0];
  if (!artifact?.storage_path) {
    return NextResponse.json({ error: 'artifact_missing' }, { status: 404 });
  }

  const { data: file, error } = await supabase.storage
    .from('research-reports')
    .download(artifact.storage_path);
  if (error || !file) {
    return NextResponse.json({ error: 'download_failed', detail: error?.message }, { status: 500 });
  }

  const filename = `${job.mode === 'ump_only' ? 'UMP-UMS' : job.mode === 'angle' ? 'Angle-Research' : 'Research'}-${job.brand}-${job.created_at.slice(0, 10)}.${format === 'docx' ? 'docx' : 'md'}`;
  const contentType =
    format === 'docx'
      ? 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      : 'text/markdown; charset=utf-8';

  return new NextResponse(file, {
    headers: {
      'content-type': contentType,
      'content-disposition': `attachment; filename="${encodeURIComponent(filename)}"`,
    },
  });
}
