'use client';

import { useMemo, useState, useTransition } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { clsx } from 'clsx';
import type { ClientRow, JobRow } from '@/lib/db/jobs';
import type { ResearchMode, PipelineStep } from '@research-hub/shared';

const MODE_TABS: { value: ResearchMode; label: string; hint: string }[] = [
  { value: 'full', label: 'Full', hint: '~27 min · ~$2.77 · komplette Pipeline' },
  { value: 'angle', label: 'Angle', hint: '~12 min · ~$1.20 · R1+R2 ohne R3' },
  { value: 'ump_only', label: 'UMP/UMS', hint: '~7 min · ~$3.50 · nur R3 auf Basis einer Full-Research' },
  { value: 'custom', label: 'Custom', hint: 'freie Step-Auswahl' },
];

const CUSTOM_STEPS: { value: PipelineStep; label: string; requires?: PipelineStep[] }[] = [
  { value: 'step0_scrape', label: 'Step 0: Produktscrape + Briefing' },
  { value: 'r1a', label: 'R1a: Zielgruppe Kat. 01-13' },
  { value: 'r1b', label: 'R1b: Zielgruppe Kat. 14-25' },
  { value: 'r2_voc', label: 'R2: Voice of Customer' },
  { value: 'r3_prefetch', label: 'R3-Prefetch: Studien-Crossref' },
  { value: 'r2_synth', label: 'R2-Synth: Belief Architecture', requires: ['r1a', 'r2_voc'] },
  { value: 'r3_scientist', label: 'R3-Scientist: UMP/UMS (Opus)', requires: ['r3_prefetch'] },
  { value: 'quality_review', label: 'Quality Review' },
  { value: 'repair', label: 'Targeted Repair', requires: ['quality_review'] },
  { value: 'assembly_export', label: 'Assembly + MD/DOCX-Export' },
];

export function NewJobForm({ clients, priorJobs }: { clients: ClientRow[]; priorJobs: JobRow[] }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const [clientId, setClientId] = useState<string>(clients[0]?.id ?? '');
  const [mode, setMode] = useState<ResearchMode>('full');
  const [url, setUrl] = useState('');
  const [brand, setBrand] = useState('');
  const [productName, setProductName] = useState('');
  const [angle, setAngle] = useState('');
  const [sourceJobId, setSourceJobId] = useState<string>('');
  const [customSteps, setCustomSteps] = useState<PipelineStep[]>([
    'step0_scrape',
    'r1a',
    'r2_voc',
    'assembly_export',
  ]);

  const selectedClient = useMemo(
    () => clients.find((c) => c.id === clientId) ?? null,
    [clients, clientId],
  );

  // Prefill brand + URL from client on change
  function onClientChange(id: string) {
    setClientId(id);
    const c = clients.find((x) => x.id === id);
    if (c) {
      if (!brand) setBrand(c.name);
    }
  }

  const clientPriorJobs = priorJobs.filter((j) => j.client_id === clientId);

  const customStepErrors: string[] = [];
  if (mode === 'custom') {
    for (const s of CUSTOM_STEPS) {
      if (customSteps.includes(s.value) && s.requires) {
        for (const req of s.requires) {
          if (!customSteps.includes(req)) {
            customStepErrors.push(`${s.label} benötigt: ${req}`);
          }
        }
      }
    }
    if (customSteps.length === 0) customStepErrors.push('Mindestens ein Step erforderlich');
  }

  function toggleStep(step: PipelineStep) {
    setCustomSteps((prev) =>
      prev.includes(step) ? prev.filter((s) => s !== step) : [...prev, step],
    );
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (mode === 'ump_only' && !sourceJobId) {
      setError('Für UMP/UMS-only musst du eine vorherige Full-Research auswählen.');
      return;
    }
    if (mode === 'custom' && customStepErrors.length > 0) {
      setError(customStepErrors.join(' · '));
      return;
    }

    const payload = {
      clientId,
      mode,
      url: url.trim(),
      brand: brand.trim(),
      productName: productName.trim() || undefined,
      angle: angle.trim(),
      sourceJobId: mode === 'ump_only' ? sourceJobId : undefined,
      customSteps: mode === 'custom' ? customSteps : undefined,
    };

    startTransition(async () => {
      const res = await fetch('/api/jobs', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }));
        setError(err.error ?? 'Unbekannter Fehler');
        return;
      }
      const { jobId } = (await res.json()) as { jobId: string };
      router.push(`/jobs/${jobId}`);
    });
  }

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <section className="card p-6">
        <label htmlFor="client" className="block text-sm font-medium">
          Kunde
        </label>
        <select
          id="client"
          value={clientId}
          onChange={(e) => onClientChange(e.target.value)}
          className="mt-2 w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm"
        >
          {clients.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
              {c.industry ? ` — ${c.industry}` : ''}
              {!c.drive_folder_id ? ' (kein Drive-Ordner!)' : ''}
            </option>
          ))}
        </select>
        {selectedClient && !selectedClient.drive_folder_id && (
          <p className="mt-2 text-xs text-amber-300">
            ⚠️ Dieser Kunde hat keinen <code>drive_folder_id</code>. Der Report wird NICHT nach Drive hochgeladen — nur MD-Download verfügbar.
          </p>
        )}
      </section>

      <section className="card p-6">
        <p className="block text-sm font-medium">Modus</p>
        <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {MODE_TABS.map((m) => (
            <button
              type="button"
              key={m.value}
              onClick={() => setMode(m.value)}
              className={clsx(
                'rounded-md border px-3 py-2 text-left text-sm transition',
                mode === m.value
                  ? 'border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-accent)]'
                  : 'border-[var(--color-border)] hover:bg-white/5',
              )}
            >
              <div className="font-semibold">{m.label}</div>
              <div className="mt-0.5 text-xs opacity-80">{m.hint}</div>
            </button>
          ))}
        </div>
      </section>

      <section className="card space-y-4 p-6">
        <div>
          <label htmlFor="url" className="block text-sm font-medium">
            Produkt-URL
          </label>
          <input
            id="url"
            type="url"
            required
            placeholder="https://…"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="mt-2 w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm"
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="brand" className="block text-sm font-medium">
              Marke
            </label>
            <input
              id="brand"
              type="text"
              required
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              className="mt-2 w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label htmlFor="product" className="block text-sm font-medium">
              Produktname <span className="text-[var(--color-text-muted)]">(optional)</span>
            </label>
            <input
              id="product"
              type="text"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              className="mt-2 w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div>
          <label htmlFor="angle" className="block text-sm font-medium">
            Angle / Thema
          </label>
          <textarea
            id="angle"
            required
            rows={2}
            placeholder="z.B. Stress-Schalter — erhöhtes Cortisol bei Frauen, die alles managen müssen"
            value={angle}
            onChange={(e) => setAngle(e.target.value)}
            className="mt-2 w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm"
          />
        </div>
      </section>

      {mode === 'ump_only' && (
        <section className="card p-6">
          <label htmlFor="source" className="block text-sm font-medium">
            Vorherige Full-Research (als R1/R2-Quelle)
          </label>
          {clientPriorJobs.length === 0 ? (
            <p className="mt-2 text-sm text-amber-300">
              Kein abgeschlossener Job für diesen Kunden. Bitte erst eine Full-Research laufen lassen
              oder einen anderen Modus wählen.
            </p>
          ) : (
            <select
              id="source"
              value={sourceJobId}
              onChange={(e) => setSourceJobId(e.target.value)}
              required
              className="mt-2 w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm"
            >
              <option value="">– auswählen –</option>
              {clientPriorJobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.brand} — {j.angle.slice(0, 60)}
                  {j.angle.length > 60 ? '…' : ''} ({new Date(j.created_at).toLocaleDateString('de-DE')})
                </option>
              ))}
            </select>
          )}
        </section>
      )}

      {mode === 'custom' && (
        <section className="card p-6">
          <p className="block text-sm font-medium">Steps auswählen</p>
          <div className="mt-3 grid gap-2">
            {CUSTOM_STEPS.map((s) => (
              <label
                key={s.value}
                className="flex cursor-pointer items-start gap-3 rounded-md border border-[var(--color-border)] px-3 py-2 hover:bg-white/5"
              >
                <input
                  type="checkbox"
                  checked={customSteps.includes(s.value)}
                  onChange={() => toggleStep(s.value)}
                  className="mt-0.5"
                />
                <div>
                  <div className="text-sm">{s.label}</div>
                  {s.requires && (
                    <div className="text-xs text-[var(--color-text-muted)]">
                      Benötigt: {s.requires.join(', ')}
                    </div>
                  )}
                </div>
              </label>
            ))}
          </div>
          {customStepErrors.length > 0 && (
            <ul className="mt-3 space-y-1 text-xs text-red-300">
              {customStepErrors.map((e) => (
                <li key={e}>• {e}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {error && (
        <div className="rounded-md border border-red-900/50 bg-red-950/40 p-3 text-sm text-red-200">
          {error}
        </div>
      )}

      <div className="flex justify-end gap-3">
        <Link
          href="/"
          className="rounded-md border border-[var(--color-border)] px-4 py-2 text-sm hover:bg-white/5"
        >
          Abbrechen
        </Link>
        <button
          type="submit"
          disabled={pending}
          className="rounded-md bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-zinc-950 hover:brightness-110 disabled:opacity-50"
        >
          {pending ? 'Wird erstellt…' : 'Research starten'}
        </button>
      </div>
    </form>
  );
}
