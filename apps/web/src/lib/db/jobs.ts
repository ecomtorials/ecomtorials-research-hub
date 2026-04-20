import { createSupabaseServerClient, createSupabaseServiceRoleClient } from '@/lib/supabase/server';
import type { ResearchMode, PipelineStep, JobStatus } from '@research-hub/shared';

export interface JobRow {
  id: string;
  client_id: string;
  user_id: string;
  mode: ResearchMode;
  custom_steps: PipelineStep[] | null;
  source_job_id: string | null;
  url: string;
  brand: string;
  product_name: string | null;
  angle: string;
  status: JobStatus;
  cost_usd: number;
  quality_score: number | null;
  error: string | null;
  drive_folder_url: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobStepRow {
  id: number;
  job_id: string;
  step: PipelineStep;
  status: 'pending' | 'running' | 'succeeded' | 'failed' | 'skipped';
  started_at: string | null;
  finished_at: string | null;
  cost_usd: number;
  chars_produced: number | null;
  turns: number | null;
  log: string | null;
}

export interface ClientRow {
  id: string;
  name: string;
  industry: string | null;
  drive_folder_id: string | null;
  defaultPageUrl: string | null;
  logoUrl: string | null;
  isActive: boolean | null;
}

export async function listJobs(limit = 25): Promise<JobRow[]> {
  const supabase = await createSupabaseServerClient();
  const { data, error } = await supabase
    .schema('research')
    .from('jobs')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(limit);
  if (error) throw new Error(`listJobs failed: ${error.message}`);
  return (data ?? []) as JobRow[];
}

export async function getJob(jobId: string): Promise<JobRow | null> {
  const supabase = await createSupabaseServerClient();
  const { data, error } = await supabase
    .schema('research')
    .from('jobs')
    .select('*')
    .eq('id', jobId)
    .maybeSingle();
  if (error) throw new Error(`getJob failed: ${error.message}`);
  return data as JobRow | null;
}

export async function getJobSteps(jobId: string): Promise<JobStepRow[]> {
  const supabase = await createSupabaseServerClient();
  const { data, error } = await supabase
    .schema('research')
    .from('job_steps')
    .select('*')
    .eq('job_id', jobId)
    .order('id', { ascending: true });
  if (error) throw new Error(`getJobSteps failed: ${error.message}`);
  return (data ?? []) as JobStepRow[];
}

// clients is a shared table across projects and has service-role-only RLS.
// We check that the caller is authenticated (+ @ecomtorials.de) at the route
// layer, then read via service role — safer than loosening the RLS policy for
// a table other tools depend on.
export async function listClients(): Promise<ClientRow[]> {
  const supabase = createSupabaseServiceRoleClient();
  const { data, error } = await supabase
    .from('clients')
    .select('id, name, industry, drive_folder_id, defaultPageUrl, logoUrl, isActive')
    .order('name', { ascending: true });
  if (error) throw new Error(`listClients failed: ${error.message}`);
  return (data ?? []) as ClientRow[];
}

export async function getClient(clientId: string): Promise<ClientRow | null> {
  const supabase = createSupabaseServiceRoleClient();
  const { data, error } = await supabase
    .from('clients')
    .select('id, name, industry, drive_folder_id, defaultPageUrl, logoUrl, isActive')
    .eq('id', clientId)
    .maybeSingle();
  if (error) throw new Error(`getClient failed: ${error.message}`);
  return data as ClientRow | null;
}

export async function insertJob(input: {
  clientId: string;
  userId: string;
  mode: ResearchMode;
  customSteps?: PipelineStep[];
  sourceJobId?: string;
  url: string;
  brand: string;
  productName?: string;
  angle: string;
}): Promise<JobRow> {
  const supabase = createSupabaseServiceRoleClient();
  const { data, error } = await supabase
    .schema('research')
    .from('jobs')
    .insert({
      client_id: input.clientId,
      user_id: input.userId,
      mode: input.mode,
      custom_steps: input.customSteps ?? null,
      source_job_id: input.sourceJobId ?? null,
      url: input.url,
      brand: input.brand,
      product_name: input.productName ?? null,
      angle: input.angle,
      status: 'queued',
    })
    .select('*')
    .single();
  if (error) throw new Error(`insertJob failed: ${error.message}`);
  return data as JobRow;
}
