"""Job progress tracking — pushes step + job updates to Supabase.

Schema mirrors research.job_steps and research.jobs. All writes go via the
service-role client, bypassing RLS.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable

from supabase_client import get_supabase

log = logging.getLogger(__name__)

StepName = str  # see packages/shared/src/types.ts::PipelineStep
StepStatus = str  # 'pending'|'running'|'succeeded'|'failed'|'skipped'
JobStatus = str  # 'queued'|'running'|'succeeded'|...
AgentRole = str  # see research.agent_role enum + drain_query agent_name mapping

# Maps the free-form `agent_name` that drain_query emits (e.g. "R1a", "R3-Scientist")
# to the research.agent_role enum values. Unknown labels produce None and are
# silently dropped — the emitter must not block the pipeline.
_AGENT_NAME_TO_ROLE: dict[str, AgentRole] = {
    "Step0-Analyse": "step0",
    "R1a": "r1a",
    "R1b": "r1b",
    "R2-VoC": "r2_voc",
    "R3-Prefetch": "r3_prefetch",
    "R3-Scientist": "r3_scientist",
    "R3-Repair": "r3_scientist",
    "R2-VoC-Repair": "r2_voc",
    "R1a-Repair": "r1a",
    "R1b-Repair": "r1b",
}


def _role_from_agent_name(agent_name: str) -> AgentRole | None:
    if agent_name in _AGENT_NAME_TO_ROLE:
        return _AGENT_NAME_TO_ROLE[agent_name]
    # Some repair agents come as "{target}-Repair" — try a loose match.
    for key, role in _AGENT_NAME_TO_ROLE.items():
        if agent_name.startswith(key.split("-", 1)[0]):
            return role
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def update_job(job_id: str, **fields: Any) -> None:
    """Update fields on research.jobs. Any timestamptz values should be ISO strings."""
    sb = get_supabase()
    sb.schema("research").table("jobs").update(fields).eq("id", job_id).execute()


def mark_job_running(job_id: str) -> None:
    update_job(job_id, status="running", started_at=_now_iso())


def mark_job_finished(job_id: str, status: JobStatus, cost_usd: float, quality_score: float | None, error: str | None = None, drive_folder_url: str | None = None) -> None:
    update_job(
        job_id,
        status=status,
        finished_at=_now_iso(),
        cost_usd=round(cost_usd, 4),
        quality_score=quality_score,
        error=error,
        drive_folder_url=drive_folder_url,
    )


def start_step(job_id: str, step: StepName) -> None:
    sb = get_supabase()
    sb.schema("research").table("job_steps").upsert(
        {
            "job_id": job_id,
            "step": step,
            "status": "running",
            "started_at": _now_iso(),
        },
        on_conflict="job_id,step",
    ).execute()
    # Mirror as an activity row so the live swarm UI can highlight this agent
    # as soon as it spawns. Step name maps 1:1 to research.agent_role.
    _safe_insert_activity(job_id, step, "agent_spawn")


def finish_step(
    job_id: str,
    step: StepName,
    status: StepStatus,
    cost_usd: float = 0.0,
    chars_produced: int | None = None,
    turns: int | None = None,
    log_text: str | None = None,
) -> None:
    sb = get_supabase()
    sb.schema("research").table("job_steps").upsert(
        {
            "job_id": job_id,
            "step": step,
            "status": status,
            "finished_at": _now_iso(),
            "cost_usd": round(cost_usd, 4),
            "chars_produced": chars_produced,
            "turns": turns,
            "log": log_text,
        },
        on_conflict="job_id,step",
    ).execute()
    # Mirror as an activity row so the swarm UI can retire the agent orb.
    _safe_insert_activity(job_id, step, "agent_finish", detail=log_text)


# ---------------------------------------------------------------------------
# Activity emitter (live MCP tool-call events, agent spawn/finish)
# ---------------------------------------------------------------------------
def insert_activity(
    job_id: str,
    agent: AgentRole,
    kind: str,
    tool: str | None = None,
    detail: str | None = None,
) -> None:
    """Insert a row into research.job_activity. Detail is truncated to 200 chars."""
    if detail is not None and len(detail) > 200:
        detail = detail[:197] + "..."
    sb = get_supabase()
    sb.schema("research").table("job_activity").insert(
        {
            "job_id": job_id,
            "agent": agent,
            "kind": kind,
            "tool": tool,
            "detail": detail,
        }
    ).execute()


def _safe_insert_activity(
    job_id: str,
    agent: AgentRole,
    kind: str,
    tool: str | None = None,
    detail: str | None = None,
) -> None:
    """Never raises — activity instrumentation must not break the pipeline."""
    try:
        insert_activity(job_id, agent, kind, tool=tool, detail=detail)
    except Exception as e:  # noqa: BLE001
        log.warning("insert_activity failed: %s (job=%s agent=%s kind=%s)", e, job_id, agent, kind)


def make_agent_emitter(job_id: str) -> Callable[[str, str, Any], None]:
    """Return a closure for pipeline.agents.activity_emitter.

    drain_query calls it as emitter(agent_name, tool_name, tool_input).
    We map agent_name→AgentRole via _AGENT_NAME_TO_ROLE and insert a
    tool_call activity row.
    """
    def _emit(agent_name: str, tool_name: str, tool_input: Any) -> None:
        role = _role_from_agent_name(agent_name)
        if role is None:
            return
        # Serialize tool_input safely — most are dicts with a "query" key.
        try:
            detail_raw = (
                json.dumps(tool_input, ensure_ascii=False)
                if not isinstance(tool_input, str)
                else tool_input
            )
        except (TypeError, ValueError):
            detail_raw = str(tool_input)
        _safe_insert_activity(job_id, role, "tool_call", tool=tool_name, detail=detail_raw)

    return _emit


def register_artifact(
    job_id: str,
    kind: str,
    storage_path: str | None = None,
    drive_file_id: str | None = None,
    drive_url: str | None = None,
    size_bytes: int = 0,
) -> None:
    sb = get_supabase()
    sb.schema("research").table("job_artifacts").insert(
        {
            "job_id": job_id,
            "kind": kind,
            "storage_path": storage_path,
            "drive_file_id": drive_file_id,
            "drive_url": drive_url,
            "size_bytes": size_bytes,
        }
    ).execute()
