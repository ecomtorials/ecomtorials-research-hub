'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useState, useTransition } from 'react';
import { Search, X } from 'lucide-react';
import type { ClientRow } from '@/lib/db/jobs';

const STATUS_OPTIONS = [
  { value: 'all', label: 'Alle Status' },
  { value: 'running', label: 'Läuft' },
  { value: 'queued', label: 'Queued' },
  { value: 'succeeded', label: 'Fertig' },
  { value: 'completed_with_warnings', label: 'Fertig (Warnungen)' },
  { value: 'failed', label: 'Fehler' },
  { value: 'cancelled', label: 'Abgebrochen' },
];

const MODE_OPTIONS = [
  { value: 'all', label: 'Alle Modi' },
  { value: 'full', label: 'Full Research' },
  { value: 'angle', label: 'Angle-based' },
  { value: 'ump_only', label: 'Unique Mechanism' },
  { value: 'custom', label: 'Custom (legacy)' },
];

export function DashboardFilters({
  clients,
  currentStatus,
  currentMode,
  currentClient,
  currentSearch,
  currentPageSize,
}: {
  clients: ClientRow[];
  currentStatus: string;
  currentMode: string;
  currentClient: string;
  currentSearch: string;
  currentPageSize: number;
}) {
  const router = useRouter();
  const params = useSearchParams();
  const [pending, startTransition] = useTransition();
  const [search, setSearch] = useState(currentSearch);

  // Keep local search input in sync when filters are reset externally.
  useEffect(() => {
    setSearch(currentSearch);
  }, [currentSearch]);

  const push = useCallback(
    (patch: Record<string, string | null>) => {
      const sp = new URLSearchParams(params.toString());
      for (const [k, v] of Object.entries(patch)) {
        if (v === null || v === '' || v === 'all') sp.delete(k);
        else sp.set(k, v);
      }
      // Reset to page 1 when filters change (unless the patch itself sets page)
      if (!('page' in patch)) sp.delete('page');
      startTransition(() => router.push(`/?${sp.toString()}`));
    },
    [params, router],
  );

  function onSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    push({ q: search.trim() || null });
  }

  const hasAnyFilter =
    currentStatus !== 'all' ||
    currentMode !== 'all' ||
    currentClient !== 'all' ||
    currentSearch !== '';

  return (
    <div className="card flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:items-center">
        <select
          value={currentStatus}
          onChange={(e) => push({ status: e.target.value })}
          className="input !py-1.5 !text-xs"
          disabled={pending}
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={currentMode}
          onChange={(e) => push({ mode: e.target.value })}
          className="input !py-1.5 !text-xs"
          disabled={pending}
        >
          {MODE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={currentClient}
          onChange={(e) => push({ client: e.target.value })}
          className="input !py-1.5 !text-xs"
          disabled={pending}
        >
          <option value="all">Alle Kunden</option>
          {clients.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select
          value={String(currentPageSize)}
          onChange={(e) => push({ size: e.target.value })}
          className="input !py-1.5 !text-xs"
          disabled={pending}
        >
          <option value="25">25 / Seite</option>
          <option value="50">50 / Seite</option>
          <option value="100">100 / Seite</option>
        </select>
      </div>

      <div className="flex items-center gap-2">
        <form onSubmit={onSearchSubmit} className="relative flex-1 sm:flex-initial">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--color-text-subtle)]" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Brand / Angle suchen…"
            className="input !py-1.5 !pl-8 !text-xs sm:w-56"
          />
        </form>
        {hasAnyFilter && (
          <button
            type="button"
            onClick={() =>
              push({ status: null, mode: null, client: null, q: null })
            }
            className="inline-flex items-center gap-1 rounded-md border border-[var(--color-border)] px-2.5 py-1.5 text-xs text-[var(--color-text-muted)] hover:bg-white/5"
            title="Filter zurücksetzen"
          >
            <X className="h-3 w-3" /> Reset
          </button>
        )}
      </div>
    </div>
  );
}
