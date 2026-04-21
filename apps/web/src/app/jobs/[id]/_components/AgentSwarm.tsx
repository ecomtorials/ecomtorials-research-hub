'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  BookOpen,
  Bot,
  CheckCircle2,
  FileText,
  Microscope,
  Package,
  Search,
  Sparkles,
  Upload,
  XCircle,
  Zap,
} from 'lucide-react';
import { clsx } from 'clsx';
import type { PipelineStep, AgentRole } from '@research-hub/shared';
import type { JobStepRow } from '@/lib/db/jobs';
import type { ActivityRow } from '@/lib/db/activity';

// ---------------------------------------------------------------------------
// Layout constants — SVG viewport 1000x420, agent and tool positions fixed.
// CSS `object-fit` handles responsive scaling; we don't recompute on resize.
// ---------------------------------------------------------------------------
const VIEW_W = 1000;
const VIEW_H = 420;

type XY = { x: number; y: number };

const AGENT_POS: Record<AgentRole, XY> = {
  step0: { x: 80, y: 210 },
  r1a: { x: 320, y: 120 },
  r1b: { x: 320, y: 300 },
  r2_voc: { x: 470, y: 120 },
  r3_prefetch: { x: 470, y: 300 },
  r2_synth: { x: 620, y: 150 },
  r3_scientist: { x: 620, y: 280 },
  quality_review: { x: 770, y: 210 },
  repair: { x: 770, y: 340 },
  assembly_export: { x: 900, y: 210 },
};

// MCP tool icons live above the research agents as an orbiting cloud.
const TOOL_POS: Record<string, XY> = {
  perplexity_fast_search: { x: 300, y: 40 },
  perplexity_pro_search: { x: 395, y: 30 },
  perplexity_academic_search: { x: 490, y: 40 },
  crossref_ingredient_search: { x: 580, y: 30 },
  crossref_validate_doi: { x: 660, y: 40 },
  pubmed_search: { x: 740, y: 30 },
  pubmed_fetch_abstract: { x: 810, y: 40 },
  gemini_search: { x: 880, y: 50 },
};

function toolIcon(tool: string) {
  if (tool.startsWith('perplexity')) return Search;
  if (tool.startsWith('crossref')) return Microscope;
  if (tool.startsWith('pubmed')) return BookOpen;
  if (tool.startsWith('gemini')) return Sparkles;
  return FileText;
}

function toolLabel(tool: string) {
  // Short human label for activity-log entries.
  const m: Record<string, string> = {
    perplexity_fast_search: 'Perplexity · fast',
    perplexity_pro_search: 'Perplexity · pro',
    perplexity_academic_search: 'Perplexity · academic',
    crossref_ingredient_search: 'CrossRef · search',
    crossref_validate_doi: 'CrossRef · DOI check',
    pubmed_search: 'PubMed · search',
    pubmed_fetch_abstract: 'PubMed · abstract',
    gemini_search: 'Gemini · grounded',
  };
  return m[tool] ?? tool;
}

// Step → AgentRole mapping for reading stepsByName. Keys are identical
// except that job_steps has the superset of enum values we want here.
const STEP_TO_ROLE: Record<PipelineStep, AgentRole> = {
  step0_scrape: 'step0',
  r1a: 'r1a',
  r1b: 'r1b',
  r2_voc: 'r2_voc',
  r3_prefetch: 'r3_prefetch',
  r2_synth: 'r2_synth',
  r3_scientist: 'r3_scientist',
  quality_review: 'quality_review',
  repair: 'repair',
  assembly_export: 'assembly_export',
};

type AgentState = 'pending' | 'running' | 'succeeded' | 'failed' | 'skipped';

function agentState(stepsByName: Record<PipelineStep, JobStepRow | undefined>, role: AgentRole): AgentState {
  // Reverse lookup: find the PipelineStep key whose role == role.
  const stepKey = Object.keys(STEP_TO_ROLE).find(
    (k) => STEP_TO_ROLE[k as PipelineStep] === role,
  ) as PipelineStep | undefined;
  if (!stepKey) return 'pending';
  const s = stepsByName[stepKey];
  if (!s) return 'pending';
  return s.status as AgentState;
}

const AGENT_LABEL: Record<AgentRole, string> = {
  step0: 'Step 0 · Scrape',
  r1a: 'R1a · Zielgruppe 01-13',
  r1b: 'R1b · Zielgruppe 14-25',
  r2_voc: 'R2 · VoC',
  r3_prefetch: 'R3 · Studien',
  r2_synth: 'R2-Synth · Belief',
  r3_scientist: 'R3 · Scientist (Opus)',
  quality_review: 'Quality Gate',
  repair: 'Repair',
  assembly_export: 'Assembly + Export',
};

const STATE_COLOR: Record<AgentState, string> = {
  pending: 'stroke-zinc-700 fill-zinc-900 text-zinc-500',
  running: 'stroke-sky-400 fill-sky-950 text-sky-100',
  succeeded: 'stroke-emerald-400 fill-emerald-950 text-emerald-100',
  failed: 'stroke-red-400 fill-red-950 text-red-100',
  skipped: 'stroke-zinc-600 fill-zinc-950 text-zinc-500',
};

// ---------------------------------------------------------------------------
// Particle model — one per tool_call event, auto-retires after 900ms.
// ---------------------------------------------------------------------------
interface Particle {
  key: string;
  from: XY;
  to: XY;
  color: string;
}

const MAX_PARTICLES = 12;

function particleColor(agent: AgentRole): string {
  switch (agent) {
    case 'r1a':
      return '#60a5fa'; // blue-400
    case 'r1b':
      return '#a78bfa'; // violet-400
    case 'r2_voc':
      return '#fb923c'; // orange-400
    case 'r3_prefetch':
      return '#34d399'; // emerald-400
    case 'r3_scientist':
      return '#f472b6'; // pink-400
    default:
      return '#94a3b8'; // slate-400
  }
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export function AgentSwarm({
  activity,
  stepsByName,
  overallStatus,
  qualityScore,
}: {
  activity: ActivityRow[];
  stepsByName: Record<PipelineStep, JobStepRow | undefined>;
  overallStatus: string;
  qualityScore: number | null;
}) {
  // Process activity events into (a) live particles, (b) scrolling log rows.
  const [particles, setParticles] = useState<Particle[]>([]);
  const lastSeenId = useRef<number>(0);

  useEffect(() => {
    const fresh = activity.filter((a) => a.id > lastSeenId.current && a.kind === 'tool_call' && a.tool);
    if (fresh.length === 0) return;
    lastSeenId.current = Math.max(...activity.map((a) => a.id));

    const now = Date.now();
    const additions: Particle[] = fresh.map((a, i) => {
      const from = AGENT_POS[a.agent] ?? AGENT_POS.step0;
      const toolPos = a.tool ? TOOL_POS[a.tool] : undefined;
      const to: XY = toolPos ?? { x: from.x, y: from.y - 80 };
      return {
        key: `${a.id}-${now}-${i}`,
        from,
        to,
        color: particleColor(a.agent),
      };
    });
    setParticles((prev) => [...prev, ...additions].slice(-MAX_PARTICLES));
  }, [activity]);

  const qrDiamondColor = useMemo(() => {
    const qr = stepsByName.quality_review;
    if (!qr || qr.status === 'pending') return '#374151'; // zinc-700
    if (qr.status === 'running') return '#60a5fa'; // blue-400
    if (qualityScore != null && qualityScore >= 7) return '#34d399'; // green
    if (qualityScore != null && qualityScore < 7) return '#fbbf24'; // amber
    return '#34d399';
  }, [stepsByName.quality_review, qualityScore]);

  const logRows = useMemo(() => {
    return activity.filter((a) => a.kind === 'tool_call' || a.kind === 'agent_finish').slice(-30).reverse();
  }, [activity]);

  return (
    <div className="card overflow-hidden p-0">
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-2.5">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
          Agent Swarm — Live
        </h2>
        <div className="text-xs text-[var(--color-text-muted)]">
          {activity.length} Events
          {overallStatus === 'running' ? ' · läuft' : overallStatus === 'succeeded' ? ' · fertig' : ''}
        </div>
      </div>

      <div className="relative aspect-[1000/420] w-full bg-gradient-to-b from-[#0a0c12] to-[#111520]">
        <svg
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          className="absolute inset-0 h-full w-full"
          aria-hidden="true"
        >
          {/* Connecting lines (static) */}
          <g stroke="rgba(255,255,255,0.08)" strokeWidth={1} fill="none">
            <path d={`M${AGENT_POS.step0.x},${AGENT_POS.step0.y} L${AGENT_POS.r1a.x},${AGENT_POS.r1a.y}`} />
            <path d={`M${AGENT_POS.step0.x},${AGENT_POS.step0.y} L${AGENT_POS.r1b.x},${AGENT_POS.r1b.y}`} />
            <path d={`M${AGENT_POS.step0.x},${AGENT_POS.step0.y} L${AGENT_POS.r2_voc.x},${AGENT_POS.r2_voc.y}`} />
            <path d={`M${AGENT_POS.step0.x},${AGENT_POS.step0.y} L${AGENT_POS.r3_prefetch.x},${AGENT_POS.r3_prefetch.y}`} />
            <path d={`M${AGENT_POS.r1a.x},${AGENT_POS.r1a.y} L${AGENT_POS.r2_synth.x},${AGENT_POS.r2_synth.y}`} />
            <path d={`M${AGENT_POS.r2_voc.x},${AGENT_POS.r2_voc.y} L${AGENT_POS.r2_synth.x},${AGENT_POS.r2_synth.y}`} />
            <path d={`M${AGENT_POS.r3_prefetch.x},${AGENT_POS.r3_prefetch.y} L${AGENT_POS.r3_scientist.x},${AGENT_POS.r3_scientist.y}`} />
            <path d={`M${AGENT_POS.r1b.x},${AGENT_POS.r1b.y} L${AGENT_POS.r3_scientist.x},${AGENT_POS.r3_scientist.y}`} />
            <path d={`M${AGENT_POS.r2_synth.x},${AGENT_POS.r2_synth.y} L${AGENT_POS.quality_review.x},${AGENT_POS.quality_review.y}`} />
            <path d={`M${AGENT_POS.r3_scientist.x},${AGENT_POS.r3_scientist.y} L${AGENT_POS.quality_review.x},${AGENT_POS.quality_review.y}`} />
            <path d={`M${AGENT_POS.quality_review.x},${AGENT_POS.quality_review.y} L${AGENT_POS.assembly_export.x},${AGENT_POS.assembly_export.y}`} />
          </g>

          {/* Agent orbs */}
          {(Object.keys(AGENT_POS) as AgentRole[]).map((role) => {
            if (role === 'repair') return null; // hide unless triggered (next release)
            const state = agentState(stepsByName, role);
            const pos = AGENT_POS[role];
            const r = role === 'r3_scientist' ? 32 : 26;
            return <AgentOrb key={role} role={role} pos={pos} state={state} r={r} />;
          })}

          {/* MCP tool icons */}
          {Object.entries(TOOL_POS).map(([tool, pos]) => (
            <g key={tool} transform={`translate(${pos.x - 13}, ${pos.y - 13})`}>
              <rect
                width={26}
                height={26}
                rx={6}
                className="fill-zinc-900 stroke-zinc-700"
                strokeWidth={1}
              />
              <g transform="translate(5 5)">
                <ToolIcon tool={tool} />
              </g>
            </g>
          ))}

          {/* Quality-gate diamond overlays the quality_review orb */}
          <motion.g
            animate={{ scale: stepsByName.quality_review?.status === 'running' ? [1, 1.08, 1] : 1 }}
            transition={{ repeat: Infinity, duration: 1.4 }}
            style={{ originX: `${AGENT_POS.quality_review.x}px`, originY: `${AGENT_POS.quality_review.y}px` }}
          >
            <polygon
              points={`${AGENT_POS.quality_review.x},${AGENT_POS.quality_review.y - 22} ${AGENT_POS.quality_review.x + 22},${AGENT_POS.quality_review.y} ${AGENT_POS.quality_review.x},${AGENT_POS.quality_review.y + 22} ${AGENT_POS.quality_review.x - 22},${AGENT_POS.quality_review.y}`}
              fill={qrDiamondColor}
              fillOpacity={0.2}
              stroke={qrDiamondColor}
              strokeWidth={2}
            />
            {qualityScore != null && (
              <text
                x={AGENT_POS.quality_review.x}
                y={AGENT_POS.quality_review.y + 4}
                textAnchor="middle"
                className="fill-white text-[12px] font-semibold"
              >
                {qualityScore.toFixed(1)}
              </text>
            )}
          </motion.g>

          {/* Particles for tool_call events */}
          <AnimatePresence>
            {particles.map((p) => (
              <motion.circle
                key={p.key}
                r={4}
                cx={p.from.x}
                cy={p.from.y}
                fill={p.color}
                initial={{ cx: p.from.x, cy: p.from.y, opacity: 0.9 }}
                animate={{ cx: p.to.x, cy: p.to.y, opacity: 0 }}
                transition={{ duration: 0.9, ease: 'easeOut' }}
                onAnimationComplete={() =>
                  setParticles((prev) => prev.filter((x) => x.key !== p.key))
                }
              />
            ))}
          </AnimatePresence>
        </svg>
      </div>

      {/* Activity log */}
      <div className="border-t border-[var(--color-border)] bg-black/30">
        <ul className="max-h-48 overflow-y-auto text-xs">
          {logRows.length === 0 ? (
            <li className="px-4 py-3 text-[var(--color-text-muted)]">
              Warte auf den ersten Agent-Event…
            </li>
          ) : (
            logRows.map((row) => <LogRow key={row.id} row={row} />)
          )}
        </ul>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------
function AgentOrb({ role, pos, state, r }: { role: AgentRole; pos: XY; state: AgentState; r: number }) {
  const color = STATE_COLOR[state];
  const pulsing = state === 'running';
  return (
    <g className={color} transform={`translate(${pos.x}, ${pos.y})`}>
      {pulsing && (
        <motion.circle
          r={r + 6}
          fill="none"
          stroke="currentColor"
          strokeOpacity={0.4}
          strokeWidth={1}
          animate={{ scale: [1, 1.3], opacity: [0.6, 0] }}
          transition={{ repeat: Infinity, duration: 1.4, ease: 'easeOut' }}
        />
      )}
      <circle r={r} strokeWidth={2} />
      <g transform="translate(-8 -8)">
        <AgentIcon role={role} />
      </g>
      <text
        y={r + 16}
        textAnchor="middle"
        className="fill-current text-[10px] font-medium"
      >
        {AGENT_LABEL[role]}
      </text>
      {state === 'succeeded' && (
        <g transform={`translate(${r - 6}, ${-r - 2})`}>
          <circle r={7} className="fill-emerald-500" />
          <g transform="translate(-4 -4)">
            <CheckCircle2 size={8} color="white" />
          </g>
        </g>
      )}
      {state === 'failed' && (
        <g transform={`translate(${r - 6}, ${-r - 2})`}>
          <circle r={7} className="fill-red-500" />
          <g transform="translate(-4 -4)">
            <XCircle size={8} color="white" />
          </g>
        </g>
      )}
    </g>
  );
}

function AgentIcon({ role }: { role: AgentRole }) {
  const size = 16;
  switch (role) {
    case 'step0':
      return <Package size={size} />;
    case 'r3_scientist':
      return <Zap size={size} />;
    case 'quality_review':
      return <CheckCircle2 size={size} />;
    case 'assembly_export':
      return <Upload size={size} />;
    default:
      return <Bot size={size} />;
  }
}

function ToolIcon({ tool }: { tool: string }) {
  const Icon = toolIcon(tool);
  return <Icon size={16} className="text-zinc-400" />;
}

function LogRow({ row }: { row: ActivityRow }) {
  const Icon = row.tool ? toolIcon(row.tool) : Bot;
  const t = new Date(row.created_at);
  const ts = `${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}:${String(t.getSeconds()).padStart(2, '0')}`;
  const agentLabel = AGENT_LABEL[row.agent] ?? row.agent;
  const kindLabel = row.kind === 'tool_call' ? '→' : row.kind === 'agent_finish' ? '✓' : row.kind;
  const queryStr = extractQuery(row.detail);

  return (
    <li
      className={clsx(
        'grid grid-cols-[auto_auto_1fr_auto] items-center gap-3 border-b border-white/5 px-4 py-1.5 last:border-b-0',
        row.kind === 'agent_finish' && 'text-emerald-300/80',
      )}
    >
      <span className="font-mono text-[10px] text-[var(--color-text-muted)]">{ts}</span>
      <span className="flex items-center gap-1.5">
        <Icon size={12} className="text-zinc-400" />
        <span className="text-xs font-medium">{agentLabel}</span>
      </span>
      <span className="min-w-0 truncate text-xs text-[var(--color-text-muted)]">
        {kindLabel} {row.tool ? toolLabel(row.tool) : ''} {queryStr && `· ${queryStr}`}
      </span>
      <span />
    </li>
  );
}

function extractQuery(detail: string | null): string {
  if (!detail) return '';
  // Most tool_input payloads are JSON with a "query" field. Fall back to raw truncated.
  try {
    const obj = JSON.parse(detail);
    if (typeof obj === 'object' && obj && typeof obj.query === 'string') {
      return `"${obj.query.slice(0, 80)}"`;
    }
  } catch {
    /* not JSON */
  }
  return detail.length > 80 ? detail.slice(0, 80) + '…' : detail;
}
