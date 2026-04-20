import { clsx } from 'clsx';
import type { ResearchMode, JobStatus } from '@research-hub/shared';

const MODE_LABEL: Record<ResearchMode, string> = {
  full: 'Full',
  angle: 'Angle',
  ump_only: 'UMP/UMS',
  custom: 'Custom',
};

const MODE_COLOR: Record<ResearchMode, string> = {
  full: 'bg-cyan-950/50 text-cyan-300 border-cyan-900',
  angle: 'bg-purple-950/50 text-purple-300 border-purple-900',
  ump_only: 'bg-amber-950/50 text-amber-300 border-amber-900',
  custom: 'bg-zinc-900 text-zinc-300 border-zinc-800',
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
  queued: 'bg-zinc-900 text-zinc-300 border-zinc-800',
  running: 'bg-blue-950/50 text-blue-300 border-blue-900 animate-pulse',
  succeeded: 'bg-emerald-950/50 text-emerald-300 border-emerald-900',
  failed: 'bg-red-950/50 text-red-300 border-red-900',
  cancelled: 'bg-zinc-900 text-zinc-400 border-zinc-800',
  completed_with_warnings: 'bg-amber-950/50 text-amber-300 border-amber-900',
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
