'use client';

import { useEffect, useMemo, useState } from 'react';
import { clsx } from 'clsx';
import { createSupabaseBrowserClient } from '@/lib/supabase/browser';
import type { JobRow, JobStepRow } from '@/lib/db/jobs';
import type { ActivityRow } from '@/lib/db/activity';
import type { PipelineStep } from '@research-hub/shared';
import { AgentSwarm } from './AgentSwarm';

const STEP_LABELS: Record<PipelineStep, string> = {
  step0_scrape: 'Step 0 · Produktscrape + Briefing',
  r1a: 'R1a · Zielgruppe Kat. 01-13',
  r1b: 'R1b · Zielgruppe Kat. 14-25',
  r2_voc: 'R2 · Voice of Customer',
  r3_prefetch: 'R3-Prefetch · Studien-Crossref',
  r2_synth: 'R2-Synth · Belief Architecture',
  r3_scientist: 'R3-Scientist · UMP/UMS (Opus)',
  quality_review: 'Quality Review',
  repair: 'Targeted Repair',
  assembly_export: 'Assembly + MD/DOCX-Export',
};

const STATUS_ICON: Record<JobStepRow['status'], string> = {
  pending: '○',
  running: '◐',
  succeeded: '●',
  failed: '✕',
  skipped: '–',
};

const STATUS_COLOR: Record<JobStepRow['status'], string> = {
  pending: 'text-zinc-600',
  running: 'text-blue-400 animate-pulse',
  succeeded: 'text-emerald-400',
  failed: 'text-red-400',
  skipped: 'text-zinc-500',
};

export function JobProgress({
  jobId,
  initialJob,
  initialSteps,
  initialActivity,
}: {
  jobId: string;
  initialJob: JobRow;
  initialSteps: JobStepRow[];
  initialActivity: ActivityRow[];
}) {
  const [job, setJob] = useState(initialJob);
  const [steps, setSteps] = useState(initialSteps);
  const [activity, setActivity] = useState<ActivityRow[]>(initialActivity);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    const supabase = createSupabaseBrowserClient();

    const channel = supabase
      .channel(`job-${jobId}`)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'research',
          table: 'jobs',
          filter: `id=eq.${jobId}`,
        },
        (payload) => {
          if (payload.eventType === 'UPDATE' && payload.new) {
            setJob(payload.new as JobRow);
          }
        },
      )
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'research',
          table: 'job_steps',
          filter: `job_id=eq.${jobId}`,
        },
        (payload) => {
          setSteps((prev) => {
            const row = (payload.new ?? payload.old) as JobStepRow;
            if (!row) return prev;
            if (payload.eventType === 'DELETE') {
              return prev.filter((s) => s.id !== row.id);
            }
            const existing = prev.findIndex((s) => s.id === row.id);
            if (existing >= 0) {
              const next = [...prev];
              next[existing] = row;
              return next;
            }
            return [...prev, row].sort((a, b) => a.id - b.id);
          });
        },
      )
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'research',
          table: 'job_activity',
          filter: `job_id=eq.${jobId}`,
        },
        (payload) => {
          const row = payload.new as ActivityRow;
          if (!row) return;
          setActivity((prev) => {
            // Append-only with bounded buffer so long-running jobs don't bloat memory.
            if (prev.some((a) => a.id === row.id)) return prev;
            const next = [...prev, row];
            return next.length > 300 ? next.slice(-300) : next;
          });
        },
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [jobId]);

  const totalCost = steps.reduce((acc, s) => acc + Number(s.cost_usd), 0);
  const totalChars = steps.reduce((acc, s) => acc + (s.chars_produced ?? 0), 0);

  const stepsByName = useMemo(() => {
    const map: Record<PipelineStep, JobStepRow | undefined> = {
      step0_scrape: undefined,
      r1a: undefined,
      r1b: undefined,
      r2_voc: undefined,
      r3_prefetch: undefined,
      r2_synth: undefined,
      r3_scientist: undefined,
      quality_review: undefined,
      repair: undefined,
      assembly_export: undefined,
    };
    for (const s of steps) map[s.step] = s;
    return map;
  }, [steps]);

  return (
    <div className="space-y-4">
      <AgentSwarm
        activity={activity}
        stepsByName={stepsByName}
        overallStatus={job.status}
        qualityScore={job.quality_score != null ? Number(job.quality_score) : null}
      />

      <div className="card p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
          Pipeline-Steps
        </h2>
        <div className="flex items-center gap-3 text-xs text-[var(--color-text-muted)]">
          <span>
            {steps.length} Steps · ${totalCost.toFixed(2)} · {totalChars.toLocaleString('de-DE')} Zeichen
          </span>
          <button
            type="button"
            onClick={() => setShowDetails((v) => !v)}
            className="rounded-md border border-[var(--color-border)] px-2 py-1 text-[10px] uppercase tracking-wide hover:bg-white/5"
          >
            {showDetails ? 'Verbergen' : 'Details'}
          </button>
        </div>
      </div>

      {showDetails && (
        steps.length === 0 ? (
          <p className="text-sm text-[var(--color-text-muted)]">
            Worker hat noch keinen Step gestartet. Wenn der Status „queued" bleibt, prüfe ob der Worker läuft.
          </p>
        ) : (
          <ol className="space-y-2">
            {steps.map((s) => (
              <li
                key={s.id}
                className="grid grid-cols-[auto_1fr_auto] items-start gap-3 rounded-md border border-[var(--color-border)] px-3 py-2"
              >
                <span className={clsx('mt-0.5 font-mono', STATUS_COLOR[s.status])}>
                  {STATUS_ICON[s.status]}
                </span>
                <div className="min-w-0">
                  <div className="text-sm font-medium">{STEP_LABELS[s.step]}</div>
                  {s.log && (
                    <div className="mt-1 truncate text-xs text-[var(--color-text-muted)]">
                      {s.log}
                    </div>
                  )}
                </div>
                <div className="text-right font-mono text-xs text-[var(--color-text-muted)]">
                  {Number(s.cost_usd) > 0 && <div>${Number(s.cost_usd).toFixed(3)}</div>}
                  {s.chars_produced != null && (
                    <div>{s.chars_produced.toLocaleString('de-DE')}c</div>
                  )}
                  {s.started_at && s.finished_at && (
                    <div>{elapsed(s.started_at, s.finished_at)}</div>
                  )}
                </div>
              </li>
            ))}
          </ol>
        )
      )}

      {job.status === 'queued' && (
        <p className="mt-4 text-xs text-amber-300">
          ⏳ Job ist in der Queue. Warte auf Worker…
        </p>
      )}
      </div>
    </div>
  );
}

function elapsed(startIso: string, endIso: string): string {
  const ms = new Date(endIso).getTime() - new Date(startIso).getTime();
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}m ${s % 60}s`;
}
