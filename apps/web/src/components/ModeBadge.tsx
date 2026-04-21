import { clsx } from 'clsx';
import type { ResearchMode, JobStatus } from '@research-hub/shared';

const MODE_LABEL: Record<ResearchMode, string> = {
  full: 'Full',
  angle: 'Angle',
  ump_only: 'Unique Mechanism',
  custom: 'Custom',
};

const MODE_COLOR: Record<ResearchMode, string> = {
  full: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
  angle: 'bg-purple-500/10 text-purple-300 border-purple-500/30',
  ump_only: 'bg-violet-500/10 text-violet-300 border-violet-500/30',
  custom: 'bg-zinc-800/50 text-zinc-400 border-zinc-700',
};

export function ModeBadge({ mode }: { mode: ResearchMode }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium',
        MODE_COLOR[mode],
      )}
    >
      {MODE_LABEL[mode]}
    </span>
  );
}

const STATUS_COLOR: Record<JobStatus, string> = {
  queued: 'bg-zinc-800/50 text-zinc-300 border-zinc-700',
  running: 'bg-sky-500/10 text-sky-300 border-sky-500/30 animate-pulse',
  succeeded: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
  failed: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
  cancelled: 'bg-zinc-800/50 text-zinc-400 border-zinc-700',
  completed_with_warnings: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
};

const STATUS_LABEL: Record<JobStatus, string> = {
  queued: 'Queued',
  running: 'Läuft',
  succeeded: 'Fertig',
  failed: 'Fehler',
  cancelled: 'Abgebrochen',
  completed_with_warnings: 'Fertig (Warnungen)',
};

export function StatusBadge({ status }: { status: JobStatus }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium',
        STATUS_COLOR[status],
      )}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}
