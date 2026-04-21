'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { XCircle } from 'lucide-react';

export function CancelButton({ jobId }: { jobId: string }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onClick = async () => {
    if (busy || pending) return;
    if (!confirm('Research wirklich abbrechen? Der aktuelle Step läuft noch zu Ende, danach stoppt die Pipeline.')) {
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const res = await fetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' });
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { error?: string; detail?: string };
        throw new Error(body.detail ?? body.error ?? `HTTP ${res.status}`);
      }
      // The DB write happens inside the route, but the SSR snapshot on this
      // page still shows the old status — refresh to pull the new status.
      startTransition(() => router.refresh());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'cancel failed');
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={onClick}
        disabled={busy || pending}
        className="inline-flex items-center gap-1.5 rounded-md border border-red-900/60 bg-red-950/30 px-3 py-1.5 text-xs font-medium text-red-200 transition hover:bg-red-950/60 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <XCircle size={14} />
        {busy || pending ? 'Breche ab…' : 'Abbrechen'}
      </button>
      {error && <span className="text-[10px] text-red-400">{error}</span>}
    </div>
  );
}
