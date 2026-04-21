import { createSupabaseServerClient } from '@/lib/supabase/server';
import type { AgentRole, ActivityKind } from '@research-hub/shared';

export interface ActivityRow {
  id: number;
  job_id: string;
  agent: AgentRole;
  kind: ActivityKind;
  tool: string | null;
  detail: string | null;
  created_at: string;
}

/**
 * Load the activity tail for a job so the live swarm has initial state.
 * Returns oldest-first (ascending by id) to match how realtime INSERT events append.
 */
export async function listJobActivity(jobId: string, limit = 100): Promise<ActivityRow[]> {
  const supabase = await createSupabaseServerClient();
  const { data, error } = await supabase
    .schema('research')
    .from('job_activity')
    .select('id, job_id, agent, kind, tool, detail, created_at')
    .eq('job_id', jobId)
    .order('id', { ascending: true })
    .limit(limit);
  if (error) throw new Error(`listJobActivity failed: ${error.message}`);
  return (data ?? []) as ActivityRow[];
}
