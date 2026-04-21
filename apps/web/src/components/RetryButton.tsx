'use client';

import { useRouter } from 'next/navigation';
import { useTransition, useState } from 'react';
import { RotateCw } from 'lucide-react';

export function RetryButton({ jobId }: { jobId: string }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function onClick(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    setError(null);
    startTransition(async () => {
      const res = await fetch(`/api/jobs/${jobId}/retry`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setError(err.error ?? 'retry_failed');
        return;
      }
      const { jobId: newId } = (await res.json()) as { jobId: string };
      router.push(`/jobs/${newId}`);
    });
  }

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={pending}
      title={error ? `Fehler: ${error}` : 'Retry mit gleichen Inputs'}
      className="inline-flex items-center gap-1 rounded-md border border-[var(--color-border)] px-2 py-1 text-xs text-[var(--color-text-muted)] transition hover:border-[var(--color-accent)] hover:text-[var(--color-accent)] disabled:opacity-50"
    >
      <RotateCw className={pending ? 'h-3 w-3 animate-spin' : 'h-3 w-3'} />
      Retry
    </button>
  );
}
