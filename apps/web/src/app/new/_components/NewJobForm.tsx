'use client';

import { useMemo, useState, useTransition } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { clsx } from 'clsx';
import { Sparkles, Target, Microscope, AlertTriangle, Info, ArrowRight, Clock, DollarSign, Lock } from 'lucide-react';
import type { ClientRow, JobRow } from '@/lib/db/jobs';
import type { ResearchMode } from '@research-hub/shared';

type UiMode = Exclude<ResearchMode, 'custom'>;

interface ModeSpec {
  value: UiMode;
  title: string;
  subtitle: string;
  tagline: string;
  duration: string;
  cost: string;
  icon: typeof Sparkles;
  accent: 'cyan' | 'purple' | 'violet';
  requiresPriorJob?: boolean;
}

const MODES: ModeSpec[] = [
  {
    value: 'full',
    title: 'Full Research',
    subtitle: 'Komplette Pipeline',
    tagline: 'R1 Zielgruppe + R2 Voice of Customer + R3 UMP/UMS mit Quality-Gate.',
    duration: '~27 min',
    cost: '~$2.77',
    icon: Sparkles,
    accent: 'cyan',
  },
  {
    value: 'angle',
    title: 'Angle-based Research',
    subtitle: 'Fokussiert auf einen Angle',
    tagline: 'R1 + R2 angle-zentriert. Schnell, günstig, ohne R3.',
    duration: '~12 min',
    cost: '~$1.20',
    icon: Target,
    accent: 'purple',
  },
  {
    value: 'ump_only',
    title: 'Unique Mechanism Development',
    subtitle: 'R3 auf bestehender Full-Research',
    tagline: 'CrossRef-Prefetch + Opus-Scientist baut den UMP/UMS-Kern.',
    duration: '~7 min',
    cost: '~$3.50',
    icon: Microscope,
    accent: 'violet',
    requiresPriorJob: true,
  },
];

export function NewJobForm({ clients, priorJobs }: { clients: ClientRow[]; priorJobs: JobRow[] }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const [clientId, setClientId] = useState<string>(clients[0]?.id ?? '');
  const [mode, setMode] = useState<UiMode>('full');
  const [url, setUrl] = useState('');
  const [brand, setBrand] = useState('');
  const [productName, setProductName] = useState('');
  const [angle, setAngle] = useState('');
  const [sourceJobId, setSourceJobId] = useState<string>('');

  const selectedClient = useMemo(
    () => clients.find((c) => c.id === clientId) ?? null,
    [clients, clientId],
  );

  const clientPriorJobs = useMemo(
    () => priorJobs.filter((j) => j.client_id === clientId),
    [priorJobs, clientId],
  );

  const umpAvailable = clientPriorJobs.length > 0;

  function onClientChange(id: string) {
    const previousClient = clients.find((x) => x.id === clientId);
    const nextClient = clients.find((x) => x.id === id);
    setClientId(id);
    if (nextClient) {
      if (!brand || brand === previousClient?.name) {
        setBrand(nextClient.name);
      }
    }
    setSourceJobId('');
    if (mode === 'ump_only') {
      const hasJobs = priorJobs.some((j) => j.client_id === id);
      if (!hasJobs) setMode('full');
    }
  }

  function onModeChange(next: UiMode) {
    if (next === 'ump_only' && !umpAvailable) return;
    setMode(next);
    if (next !== 'ump_only') setSourceJobId('');
  }

  const canSubmit =
    !!clientId &&
    !!url.trim() &&
    !!brand.trim() &&
    !!angle.trim() &&
    (mode !== 'ump_only' || !!sourceJobId);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (mode === 'ump_only' && !sourceJobId) {
      setError('Für Unique Mechanism Development musst du eine vorherige Full-Research auswählen.');
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
      {/* Client picker */}
      <section className="card p-6">
        <label htmlFor="client" className="block text-sm font-medium">
          Kunde
        </label>
        <select
          id="client"
          value={clientId}
          onChange={(e) => onClientChange(e.target.value)}
          className="input mt-2"
        >
          {clients.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
              {c.industry ? ` — ${c.industry}` : ''}
            </option>
          ))}
        </select>
        {selectedClient && !selectedClient.drive_folder_id && (
          <p className="mt-3 flex items-start gap-2 text-xs text-[color:var(--color-warn)]">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              Dieser Kunde hat keinen <code className="font-mono text-[11px]">drive_folder_id</code>.
              Der Report wird nicht nach Drive hochgeladen — nur MD-Download verfügbar.
            </span>
          </p>
        )}
      </section>

      {/* Mode picker */}
      <section>
        <div className="mb-3 flex items-end justify-between">
          <div>
            <p className="text-sm font-medium">Research-Modus</p>
            <p className="text-xs text-[var(--color-text-muted)]">
              Wähle wie tief die Research gehen soll.
            </p>
          </div>
        </div>
        <div
          role="radiogroup"
          aria-label="Research-Modus"
          className="grid gap-3 sm:grid-cols-3"
        >
          {MODES.map((spec) => {
            const Icon = spec.icon;
            const selected = mode === spec.value;
            const disabled = spec.requiresPriorJob && !umpAvailable;
            return (
              <button
                key={spec.value}
                type="button"
                role="radio"
                aria-checked={selected}
                aria-disabled={disabled}
                disabled={disabled}
                onClick={() => onModeChange(spec.value)}
                data-selected={selected}
                className="mode-card"
              >
                <div className="flex items-start justify-between">
                  <div
                    className={clsx(
                      'flex h-10 w-10 items-center justify-center rounded-lg border',
                      spec.accent === 'cyan' &&
                        'border-cyan-400/30 bg-cyan-400/10 text-cyan-300',
                      spec.accent === 'purple' &&
                        'border-purple-400/30 bg-purple-400/10 text-purple-300',
                      spec.accent === 'violet' &&
                        'border-violet-400/30 bg-violet-400/10 text-violet-300',
                    )}
                  >
                    <Icon className="h-5 w-5" strokeWidth={2} />
                  </div>
                  {disabled && (
                    <span className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-[var(--color-text-subtle)]">
                      <Lock className="h-3 w-3" /> gesperrt
                    </span>
                  )}
                </div>
                <div>
                  <div className="text-[15px] font-semibold leading-tight">{spec.title}</div>
                  <div className="mt-0.5 text-xs text-[var(--color-text-muted)]">
                    {spec.subtitle}
                  </div>
                </div>
                <p className="text-xs leading-relaxed text-[var(--color-text-muted)]">
                  {spec.tagline}
                </p>
                <div className="flex items-center gap-3 pt-1 text-[11px] text-[var(--color-text-subtle)]">
                  <span className="inline-flex items-center gap-1">
                    <Clock className="h-3 w-3" /> {spec.duration}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <DollarSign className="h-3 w-3" /> {spec.cost}
                  </span>
                </div>
                {disabled && (
                  <p className="text-[11px] text-[var(--color-text-subtle)]">
                    Benötigt eine abgeschlossene Full-Research für diesen Kunden.
                  </p>
                )}
              </button>
            );
          })}
        </div>
      </section>

      {/* UMP source job select (inline with mode) */}
      {mode === 'ump_only' && (
        <section className="card p-6">
          <label htmlFor="source" className="block text-sm font-medium">
            Basis: vorherige Full-Research
          </label>
          <p className="mt-1 text-xs text-[var(--color-text-muted)]">
            UMP/UMS wird auf R1- und R2-Artifacts dieses Jobs aufgebaut.
          </p>
          <select
            id="source"
            value={sourceJobId}
            onChange={(e) => setSourceJobId(e.target.value)}
            required
            className="input mt-3"
          >
            <option value="">– Full-Research auswählen –</option>
            {clientPriorJobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.brand} — {j.angle.slice(0, 60)}
                {j.angle.length > 60 ? '…' : ''} ({new Date(j.created_at).toLocaleDateString('de-DE')})
              </option>
            ))}
          </select>
        </section>
      )}

      {/* Brief inputs */}
      <section className="card space-y-5 p-6">
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
            className="input mt-2"
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
              className="input mt-2"
            />
          </div>
          <div>
            <label htmlFor="product" className="block text-sm font-medium">
              Produktname
              <span className="ml-1 text-[var(--color-text-subtle)]">(optional)</span>
            </label>
            <input
              id="product"
              type="text"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              className="input mt-2"
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
            rows={3}
            placeholder="z.B. Stress-Schalter — erhöhtes Cortisol bei Frauen, die alles managen müssen"
            value={angle}
            onChange={(e) => setAngle(e.target.value)}
            className="input mt-2 resize-none"
          />
          <p className="mt-2 flex items-start gap-1.5 text-xs text-[var(--color-text-subtle)]">
            <Info className="mt-0.5 h-3 w-3 shrink-0" />
            <span>
              Je schärfer der Angle, desto fokussierter die Research. 1–2 Sätze mit Zielgruppe und
              Problem.
            </span>
          </p>
        </div>
      </section>

      {error && (
        <div className="flex items-start gap-2 rounded-xl border border-[color:var(--color-danger)]/40 bg-[color:var(--color-danger-soft)] p-3 text-sm text-[color:var(--color-danger)]">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="flex items-center justify-between gap-3">
        <Link href="/" className="btn-secondary inline-flex">
          Abbrechen
        </Link>
        <button
          type="submit"
          disabled={pending || !canSubmit}
          className="btn-primary inline-flex items-center gap-2"
        >
          {pending ? 'Wird erstellt…' : 'Research starten'}
          {!pending && <ArrowRight className="h-4 w-4" />}
        </button>
      </div>
    </form>
  );
}
