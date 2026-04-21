'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  BookOpen,
  Bot,
  Check,
  FileText,
  Microscope,
  Package,
  Search,
  Shield,
  Sparkles,
  Upload,
  X,
  Zap,
} from 'lucide-react';
import type { PipelineStep, AgentRole } from '@research-hub/shared';
import type { JobStepRow } from '@/lib/db/jobs';
import type { ActivityRow } from '@/lib/db/activity';

// ---------------------------------------------------------------------------
// Layout — SVG viewBox is fixed; CSS object-fit handles responsive scale.
// ---------------------------------------------------------------------------
const VIEW_W = 1000;
const VIEW_H = 420;

type XY = { x: number; y: number };
type XYR = XY & { r: number };

const AGENT_POS: Record<AgentRole, XYR> = {
  step0: { x: 80, y: 210, r: 24 },
  r1a: { x: 320, y: 120, r: 24 },
  r1b: { x: 320, y: 300, r: 24 },
  r2_voc: { x: 470, y: 120, r: 24 },
  r3_prefetch: { x: 470, y: 300, r: 24 },
  r2_synth: { x: 620, y: 150, r: 24 },
  r3_scientist: { x: 620, y: 280, r: 30 },
  quality_review: { x: 770, y: 210, r: 26 },
  repair: { x: 770, y: 340, r: 22 },
  assembly_export: { x: 900, y: 210, r: 24 },
};

const TOOL_POS: Record<string, XY> = {
  perplexity_fast_search: { x: 300, y: 42 },
  perplexity_pro_search: { x: 395, y: 30 },
  perplexity_academic_search: { x: 490, y: 42 },
  crossref_ingredient_search: { x: 580, y: 30 },
  crossref_validate_doi: { x: 660, y: 42 },
  pubmed_search: { x: 740, y: 30 },
  pubmed_fetch_abstract: { x: 810, y: 42 },
  gemini_search: { x: 880, y: 52 },
};

const EDGES: [AgentRole, AgentRole][] = [
  ['step0', 'r1a'],
  ['step0', 'r1b'],
  ['step0', 'r2_voc'],
  ['step0', 'r3_prefetch'],
  ['r1a', 'r2_synth'],
  ['r2_voc', 'r2_synth'],
  ['r3_prefetch', 'r3_scientist'],
  ['r1b', 'r3_scientist'],
  ['r2_synth', 'quality_review'],
  ['r3_scientist', 'quality_review'],
  ['quality_review', 'assembly_export'],
];

const AGENT_COLOR: Record<AgentRole, string> = {
  step0: '#a1a1aa',
  r1a: '#60a5fa',
  r1b: '#a78bfa',
  r2_voc: '#fb923c',
  r3_prefetch: '#34d399',
  r2_synth: '#22d3ee',
  r3_scientist: '#f472b6',
  quality_review: '#facc15',
  repair: '#f87171',
  assembly_export: '#22d3ee',
};

type AgentState = 'pending' | 'running' | 'succeeded' | 'failed' | 'skipped';

type StatePalette = { ring: string; fill: string; text: string };
const STATE_PALETTE: Record<AgentState, StatePalette> = {
  pending: { ring: '#27272a', fill: '#0f0f12', text: '#52525b' },
  running: { ring: '#22d3ee', fill: 'rgba(8,145,178,0.15)', text: '#67e8f9' },
  succeeded: { ring: '#34d399', fill: 'rgba(6,78,59,0.25)', text: '#6ee7b7' },
  failed: { ring: '#f87171', fill: 'rgba(127,29,29,0.25)', text: '#fca5a5' },
  skipped: { ring: '#3f3f46', fill: '#0f0f12', text: '#71717a' },
};

const AGENT_LABEL: Record<AgentRole, string> = {
  step0: 'Step 0',
  r1a: 'R1a',
  r1b: 'R1b',
  r2_voc: 'R2 · VoC',
  r3_prefetch: 'R3 · Prefetch',
  r2_synth: 'R2-Synth',
  r3_scientist: 'R3-Scientist',
  quality_review: 'Quality Gate',
  repair: 'Repair',
  assembly_export: 'Assembly',
};

const AGENT_SUBLABEL: Record<AgentRole, string> = {
  step0: 'Scrape',
  r1a: 'Zielgruppe 01-13',
  r1b: 'Zielgruppe 14-25',
  r2_voc: 'Voice of Customer',
  r3_prefetch: 'Studien-Crossref',
  r2_synth: 'Belief',
  r3_scientist: 'UMP/UMS · Opus',
  quality_review: 'Review',
  repair: 'Targeted Fix',
  assembly_export: 'MD + DOCX',
};

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

// The visible roles — repair is hidden unless triggered.
const VISIBLE_ROLES: AgentRole[] = [
  'step0',
  'r1a',
  'r1b',
  'r2_voc',
  'r3_prefetch',
  'r2_synth',
  'r3_scientist',
  'quality_review',
  'assembly_export',
];

// ---------------------------------------------------------------------------
// Tool name normalization + icon/label helpers.
// ---------------------------------------------------------------------------
function normalizeToolName(tool: string): string {
  const m = tool.match(/^mcp__[^_]+(?:-[^_]+)*__(.+)$/);
  return m && m[1] ? m[1] : tool;
}

function toolIcon(tool: string) {
  const bare = normalizeToolName(tool);
  if (bare.startsWith('perplexity')) return Search;
  if (bare.startsWith('crossref')) return Microscope;
  if (bare.startsWith('pubmed')) return BookOpen;
  if (bare.startsWith('gemini')) return Sparkles;
  return FileText;
}

function toolLabel(tool: string) {
  const bare = normalizeToolName(tool);
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
  return m[bare] ?? bare;
}

function agentState(
  stepsByName: Record<PipelineStep, JobStepRow | undefined>,
  role: AgentRole,
): AgentState {
  const stepKey = Object.keys(STEP_TO_ROLE).find(
    (k) => STEP_TO_ROLE[k as PipelineStep] === role,
  ) as PipelineStep | undefined;
  if (!stepKey) return 'pending';
  const s = stepsByName[stepKey];
  if (!s) return 'pending';
  return s.status as AgentState;
}

function curvePath(a: XY, b: XY): string {
  const dx = Math.abs(b.x - a.x) * 0.5;
  return `M${a.x},${a.y} C${a.x + dx},${a.y} ${b.x - dx},${b.y} ${b.x},${b.y}`;
}

// ---------------------------------------------------------------------------
// Particle model — spawned on each tool_call event, self-retires via RAF.
// ---------------------------------------------------------------------------
interface Particle {
  key: string;
  from: XY;
  to: XY;
  color: string;
}

const MAX_PARTICLES = 14;

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
  const [particles, setParticles] = useState<Particle[]>([]);
  const [edgeHeat, setEdgeHeat] = useState<Record<string, number>>({});
  const [hoverRole, setHoverRole] = useState<AgentRole | null>(null);
  const lastSeenId = useRef<number>(0);

  // Derived agent states keyed by role — for O(1) lookup in renderers.
  const agentStates = useMemo(() => {
    const acc = {} as Record<AgentRole, AgentState>;
    for (const role of VISIBLE_ROLES) acc[role] = agentState(stepsByName, role);
    acc.repair = agentState(stepsByName, 'repair');
    return acc;
  }, [stepsByName]);

  // Running count for the HUD.
  const runningCount = useMemo(
    () => VISIBLE_ROLES.filter((r) => agentStates[r] === 'running').length,
    [agentStates],
  );

  // Calls per agent — displayed as badges on each orb.
  const callsPerAgent = useMemo(() => {
    const acc: Partial<Record<AgentRole, number>> = {};
    for (const a of activity) {
      if (a.kind === 'tool_call') acc[a.agent] = (acc[a.agent] ?? 0) + 1;
    }
    return acc;
  }, [activity]);

  // Spawn particles + bump edge heat on new tool_call events.
  useEffect(() => {
    const fresh = activity.filter(
      (a) => a.id > lastSeenId.current && a.kind === 'tool_call' && a.tool,
    );
    if (fresh.length === 0) return;
    lastSeenId.current = Math.max(...activity.map((a) => a.id));

    const now = Date.now();
    const adds: Particle[] = fresh
      .map((a, i): Particle | null => {
        const from = AGENT_POS[a.agent];
        if (!from) return null;
        const bare = a.tool ? normalizeToolName(a.tool) : null;
        const to = bare ? TOOL_POS[bare] : null;
        if (!to) return null;
        return {
          key: `${a.id}-${now}-${i}`,
          from: { x: from.x, y: from.y },
          to,
          color: AGENT_COLOR[a.agent] ?? '#94a3b8',
        };
      })
      .filter((p): p is Particle => p !== null);

    if (adds.length > 0) {
      setParticles((prev) => [...prev, ...adds].slice(-MAX_PARTICLES));
    }

    setEdgeHeat((prev) => {
      const next = { ...prev };
      for (const f of fresh) {
        for (const [a, b] of EDGES) {
          if (a === f.agent || b === f.agent) {
            const k = `${a}-${b}`;
            next[k] = Math.min(1, (next[k] ?? 0) + 0.3);
          }
        }
      }
      return next;
    });
  }, [activity]);

  // Heat bleed-off every 120ms — cheap enough to run on an interval.
  useEffect(() => {
    const id = setInterval(() => {
      setEdgeHeat((prev) => {
        const next: Record<string, number> = {};
        let changed = false;
        for (const [k, v] of Object.entries(prev)) {
          const nv = v * 0.94;
          if (nv > 0.02) next[k] = nv;
          else changed = true;
        }
        if (!changed && Object.keys(next).length === Object.keys(prev).length) return prev;
        return next;
      });
    }, 120);
    return () => clearInterval(id);
  }, []);

  const qrDiamondColor = useMemo(() => {
    const qr = stepsByName.quality_review;
    if (!qr || qr.status === 'pending') return 'rgba(250,204,21,0.25)';
    if (qr.status === 'running') return '#facc15';
    if (qualityScore != null && qualityScore >= 7) return '#34d399';
    if (qualityScore != null && qualityScore < 7) return '#fbbf24';
    return '#34d399';
  }, [stepsByName.quality_review, qualityScore]);

  const logRows = useMemo(() => {
    return activity
      .filter((a) => a.kind === 'tool_call' || a.kind === 'agent_finish')
      .slice(-40)
      .reverse();
  }, [activity]);

  const hoverAgent = hoverRole
    ? {
        role: hoverRole,
        label: AGENT_LABEL[hoverRole],
        sub: AGENT_SUBLABEL[hoverRole],
        state: agentStates[hoverRole] ?? 'pending',
        calls: callsPerAgent[hoverRole] ?? 0,
      }
    : null;

  return (
    <div className="card overflow-hidden p-0">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-2.5">
        <div className="flex items-center gap-2.5">
          <span
            className="rh-pulse h-1.5 w-1.5 rounded-full bg-[var(--color-accent)]"
            style={{ boxShadow: '0 0 8px var(--color-accent)' }}
          />
          <h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
            Agent Swarm — Live
          </h2>
        </div>
        <div className="font-mono text-[11px] text-[var(--color-text-muted)]">
          {activity.length} events
          {overallStatus === 'running'
            ? ' · läuft'
            : overallStatus === 'succeeded'
              ? ' · fertig'
              : overallStatus === 'failed'
                ? ' · fehler'
                : ''}
        </div>
      </div>

      {/* Canvas */}
      <div
        className="relative aspect-[1000/420] w-full"
        style={{
          background: 'radial-gradient(ellipse at 50% 60%, #0f1319 0%, #080a0e 70%)',
        }}
      >
        {/* Dot grid overlay — faded at the edges. */}
        <div
          aria-hidden
          className="absolute inset-0"
          style={{
            backgroundImage:
              'radial-gradient(circle, rgba(255,255,255,0.04) 1px, transparent 1px)',
            backgroundSize: '24px 24px',
            maskImage: 'radial-gradient(ellipse at center, black 40%, transparent 80%)',
            WebkitMaskImage:
              'radial-gradient(ellipse at center, black 40%, transparent 80%)',
          }}
        />

        <svg
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          className="absolute inset-0 h-full w-full"
          role="img"
          aria-label="Agent pipeline visualization"
        >
          <defs>
            {Object.entries(AGENT_COLOR).map(([role, c]) => (
              <radialGradient id={`rh-orb-${role}`} key={role}>
                <stop offset="0%" stopColor={c} stopOpacity="0.7" />
                <stop offset="60%" stopColor={c} stopOpacity="0.12" />
                <stop offset="100%" stopColor={c} stopOpacity="0" />
              </radialGradient>
            ))}
            <filter id="rh-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="2.2" result="b" />
              <feMerge>
                <feMergeNode in="b" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <filter id="rh-glow-strong" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="b" />
              <feMerge>
                <feMergeNode in="b" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Edge layer — base + done + active + heat */}
          <g fill="none">
            {EDGES.map(([a, b]) => {
              const pa = AGENT_POS[a];
              const pb = AGENT_POS[b];
              const heat = edgeHeat[`${a}-${b}`] ?? 0;
              const stateA = agentStates[a];
              const stateB = agentStates[b];
              const active = stateA === 'running' || stateB === 'running';
              const done =
                stateA === 'succeeded' &&
                (stateB === 'running' || stateB === 'succeeded');
              const d = curvePath(pa, pb);
              return (
                <g key={`${a}-${b}`}>
                  <path d={d} stroke="rgba(255,255,255,0.06)" strokeWidth={1} />
                  {done && (
                    <path d={d} stroke="rgba(52,211,153,0.35)" strokeWidth={1.2} />
                  )}
                  {active && (
                    <path
                      d={d}
                      stroke="var(--color-accent)"
                      strokeWidth={1.4}
                      strokeOpacity={0.55}
                      strokeDasharray="4 6"
                      className="rh-dash"
                    />
                  )}
                  {heat > 0.1 && (
                    <path
                      d={d}
                      stroke="var(--color-accent)"
                      strokeOpacity={heat * 0.6}
                      strokeWidth={1 + heat * 2}
                      filter="url(#rh-glow)"
                    />
                  )}
                </g>
              );
            })}
          </g>

          {/* Tool chips — constellation in the upper arc */}
          {Object.entries(TOOL_POS).map(([tool, p]) => {
            const Icon = toolIcon(tool);
            return (
              <g key={tool} transform={`translate(${p.x - 14},${p.y - 14})`}>
                <rect
                  width={28}
                  height={28}
                  rx={7}
                  fill="#0d0f14"
                  stroke="rgba(255,255,255,0.1)"
                  strokeWidth={1}
                />
                <foreignObject x={6} y={6} width={16} height={16}>
                  <Icon size={16} color="#a1a1aa" />
                </foreignObject>
              </g>
            );
          })}

          {/* Agent orbs */}
          {VISIBLE_ROLES.map((role) => (
            <AgentOrb
              key={role}
              role={role}
              pos={AGENT_POS[role]}
              state={agentStates[role]}
              calls={callsPerAgent[role] ?? 0}
              hovered={hoverRole === role}
              onHover={setHoverRole}
            />
          ))}

          {/* Optional repair orb — only render if it has ever moved out of pending. */}
          {agentStates.repair !== 'pending' && (
            <AgentOrb
              role="repair"
              pos={AGENT_POS.repair}
              state={agentStates.repair}
              calls={callsPerAgent.repair ?? 0}
              hovered={hoverRole === 'repair'}
              onHover={setHoverRole}
            />
          )}

          {/* Quality gate diamond */}
          <g
            transform={`translate(${AGENT_POS.quality_review.x},${AGENT_POS.quality_review.y})`}
            pointerEvents="none"
          >
            <polygon
              points="0,-28 28,0 0,28 -28,0"
              fill={`${qrDiamondColor}14`}
              stroke={qrDiamondColor}
              strokeOpacity={0.45}
              strokeWidth={1}
            />
            {qualityScore != null && stepsByName.quality_review?.status === 'succeeded' && (
              <text
                y={4}
                textAnchor="middle"
                fontSize={11}
                fontWeight={600}
                fill="#fafafa"
              >
                {qualityScore.toFixed(1)}
              </text>
            )}
          </g>

          {/* Particles — RAF-driven; each retires itself via onDone. */}
          {particles.map((p) => (
            <SwarmParticle
              key={p.key}
              particle={p}
              onDone={() =>
                setParticles((prev) => prev.filter((x) => x.key !== p.key))
              }
            />
          ))}
        </svg>

        {/* HUD — top left */}
        <div
          className="pointer-events-none absolute left-3.5 top-3 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]"
          aria-hidden
        >
          <span
            className="inline-block h-1 w-1 rounded-sm bg-emerald-400"
            style={{ boxShadow: '0 0 6px #34d399' }}
          />
          <span>
            mesh · {runningCount}/{VISIBLE_ROLES.length} active
          </span>
        </div>

        {/* Hover tooltip — top right */}
        {hoverAgent && (
          <div
            className="pointer-events-none absolute right-3.5 top-3 min-w-[180px] rounded-lg border border-[var(--color-border)] px-3 py-2.5 text-[11px] text-[var(--color-text)] backdrop-blur"
            style={{ background: 'rgba(15,17,23,0.95)' }}
          >
            <div className="font-semibold">{hoverAgent.label}</div>
            <div className="mb-1.5 text-[10px] text-[var(--color-text-muted)]">
              {hoverAgent.sub}
            </div>
            <div className="flex items-center justify-between font-mono text-[10px] text-[var(--color-text-muted)]">
              <span>status</span>
              <span style={{ color: STATE_PALETTE[hoverAgent.state].text }}>
                {hoverAgent.state}
              </span>
            </div>
            <div className="mt-1 flex items-center justify-between font-mono text-[10px] text-[var(--color-text-muted)]">
              <span>calls</span>
              <span className="text-zinc-200">{hoverAgent.calls}</span>
            </div>
          </div>
        )}
      </div>

      {/* Activity log */}
      <div
        className="border-t border-[var(--color-border)] bg-black/30"
        aria-live="polite"
      >
        <ul className="max-h-[180px] overflow-y-auto text-[11px]">
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
// AgentOrb — a single agent node, with state-driven aura/pulse/badge.
// ---------------------------------------------------------------------------
function AgentOrb({
  role,
  pos,
  state,
  calls,
  hovered,
  onHover,
}: {
  role: AgentRole;
  pos: XYR;
  state: AgentState;
  calls: number;
  hovered: boolean;
  onHover: (role: AgentRole | null) => void;
}) {
  const palette = STATE_PALETTE[state];
  const color = AGENT_COLOR[role];
  const showAura = state === 'running' || state === 'succeeded' || hovered;
  const isRunning = state === 'running';
  const isSucceeded = state === 'succeeded';
  const isFailed = state === 'failed';

  return (
    <g
      transform={`translate(${pos.x},${pos.y})`}
      style={{ cursor: 'pointer' }}
      onMouseEnter={() => onHover(role)}
      onMouseLeave={() => onHover(null)}
    >
      {showAura && (
        <circle
          r={pos.r + 22}
          fill={`url(#rh-orb-${role})`}
          opacity={isRunning ? 0.9 : 0.4}
          pointerEvents="none"
        />
      )}
      {isRunning && (
        <>
          <circle
            r={pos.r + 4}
            fill="none"
            stroke={color}
            strokeOpacity={0.5}
            strokeWidth={1}
            className="rh-ring"
            pointerEvents="none"
          />
          <circle
            r={pos.r + 4}
            fill="none"
            stroke={color}
            strokeOpacity={0.35}
            strokeWidth={1}
            className="rh-ring rh-ring-delay"
            pointerEvents="none"
          />
        </>
      )}

      <circle
        r={pos.r}
        fill={palette.fill}
        stroke={palette.ring}
        strokeWidth={1.5}
        filter={isRunning ? 'url(#rh-glow)' : undefined}
      />
      <circle
        r={pos.r - 2}
        cx={-pos.r * 0.3}
        cy={-pos.r * 0.3}
        fill="white"
        opacity={0.03}
        pointerEvents="none"
      />

      <foreignObject x={-8} y={-8} width={16} height={16}>
        <AgentIcon role={role} color={palette.text} />
      </foreignObject>

      {calls > 0 && !isSucceeded && !isFailed && (
        <g transform={`translate(${pos.r - 4},${-pos.r + 4})`} pointerEvents="none">
          <circle r={8} fill="#09090b" stroke={color} strokeWidth={1} />
          <text
            textAnchor="middle"
            dy={3}
            fontSize={9}
            fill={color}
            fontWeight={700}
            fontFamily="ui-monospace, 'SF Mono', Menlo, Consolas, monospace"
          >
            {calls}
          </text>
        </g>
      )}
      {isSucceeded && (
        <g transform={`translate(${pos.r - 4},${-pos.r + 4})`} pointerEvents="none">
          <circle r={8} fill="#10b981" />
          <foreignObject x={-5} y={-5} width={10} height={10}>
            <Check size={10} color="white" strokeWidth={3} />
          </foreignObject>
        </g>
      )}
      {isFailed && (
        <g transform={`translate(${pos.r - 4},${-pos.r + 4})`} pointerEvents="none">
          <circle r={8} fill="#ef4444" />
          <foreignObject x={-5} y={-5} width={10} height={10}>
            <X size={10} color="white" strokeWidth={3} />
          </foreignObject>
        </g>
      )}

      <text
        y={pos.r + 16}
        textAnchor="middle"
        fontSize={10}
        fontWeight={600}
        fill="#fafafa"
        pointerEvents="none"
      >
        {AGENT_LABEL[role]}
      </text>
      <text
        y={pos.r + 28}
        textAnchor="middle"
        fontSize={9}
        fill="#a1a1aa"
        pointerEvents="none"
      >
        {AGENT_SUBLABEL[role]}
      </text>
    </g>
  );
}

function AgentIcon({ role, color }: { role: AgentRole; color: string }) {
  const size = 16;
  const props = { size, color, strokeWidth: 1.8 };
  switch (role) {
    case 'step0':
      return <Package {...props} />;
    case 'r3_scientist':
      return <Zap {...props} />;
    case 'quality_review':
      return <Shield {...props} />;
    case 'assembly_export':
      return <Upload {...props} />;
    default:
      return <Bot {...props} />;
  }
}

// ---------------------------------------------------------------------------
// SwarmParticle — quadratic-bezier arc w/ trailing line, driven by RAF.
// DOM attributes are mutated directly so React doesn't re-render per frame.
// ---------------------------------------------------------------------------
function SwarmParticle({
  particle,
  onDone,
}: {
  particle: Particle;
  onDone: () => void;
}) {
  const dotRef = useRef<SVGCircleElement | null>(null);
  const tailRef = useRef<SVGLineElement | null>(null);

  useEffect(() => {
    const dot = dotRef.current;
    const tail = tailRef.current;
    if (!dot || !tail) {
      onDone();
      return;
    }

    // prefers-reduced-motion: skip the animation, just fade out.
    const prefersReduced =
      typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) {
      const t = setTimeout(onDone, 250);
      return () => clearTimeout(t);
    }

    const { from, to } = particle;
    const mx = (from.x + to.x) / 2;
    const my = Math.min(from.y, to.y) - 30;
    const start = performance.now();
    const dur = 950;
    let raf = 0;

    const bezier = (t: number) => {
      const u = 1 - t;
      return {
        x: u * u * from.x + 2 * u * t * mx + t * t * to.x,
        y: u * u * from.y + 2 * u * t * my + t * t * to.y,
      };
    };

    const tick = (now: number) => {
      const k = Math.min(1, (now - start) / dur);
      const e = 1 - Math.pow(1 - k, 3);
      const { x, y } = bezier(e);
      dot.setAttribute('cx', String(x));
      dot.setAttribute('cy', String(y));
      dot.setAttribute('opacity', String(1 - k * 0.6));
      const e2 = Math.max(0, e - 0.06);
      const { x: ex, y: ey } = bezier(e2);
      tail.setAttribute('x1', String(ex));
      tail.setAttribute('y1', String(ey));
      tail.setAttribute('x2', String(x));
      tail.setAttribute('y2', String(y));
      tail.setAttribute('opacity', String((1 - k) * 0.55));
      if (k < 1) raf = requestAnimationFrame(tick);
      else onDone();
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // We intentionally run this once per particle instance.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <g filter="url(#rh-glow-strong)" pointerEvents="none">
      <line
        ref={tailRef}
        stroke={particle.color}
        strokeWidth={1.8}
        strokeLinecap="round"
      />
      <circle
        ref={dotRef}
        r={3}
        fill={particle.color}
        cx={particle.from.x}
        cy={particle.from.y}
      />
    </g>
  );
}

// ---------------------------------------------------------------------------
// LogRow — compact live row with a colored dot per agent.
// ---------------------------------------------------------------------------
function LogRow({ row }: { row: ActivityRow }) {
  const t = new Date(row.created_at);
  const ts = `${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}:${String(t.getSeconds()).padStart(2, '0')}`;
  const agentLabel = AGENT_LABEL[row.agent] ?? row.agent;
  const color = AGENT_COLOR[row.agent] ?? '#94a3b8';
  const queryStr = extractQuery(row.detail);
  const isFinish = row.kind === 'agent_finish';
  const toolLbl = row.tool ? toolLabel(row.tool) : '';

  return (
    <li
      className="grid grid-cols-[auto_auto_1fr] items-center gap-3 border-b border-white/[0.04] px-4 py-[7px] last:border-b-0"
      style={{ borderLeft: `2px solid ${color}14` }}
    >
      <span className="font-mono text-[10px] text-[#52525b]">{ts}</span>
      <span className="flex items-center gap-1.5">
        <span
          className="inline-block h-[5px] w-[5px] rounded-full"
          style={{ background: color }}
        />
        <span className="font-medium text-[var(--color-text)]">{agentLabel}</span>
      </span>
      <span className="min-w-0 truncate text-[var(--color-text-muted)]">
        {isFinish ? '✓ finished' : '→'} {toolLbl}
        {queryStr && (
          <span className="text-[#71717a]">
            {' '}
            · &ldquo;{queryStr}&rdquo;
          </span>
        )}
      </span>
    </li>
  );
}

function extractQuery(detail: string | null): string {
  if (!detail) return '';
  try {
    const obj = JSON.parse(detail);
    if (typeof obj === 'object' && obj && typeof obj.query === 'string') {
      return obj.query.slice(0, 80);
    }
  } catch {
    /* not JSON */
  }
  return detail.length > 80 ? detail.slice(0, 80) + '…' : detail;
}
